from collections import defaultdict
from inspect import Parameter, Signature, signature
from json import dumps
from typing import Any, Callable, Literal, Optional, Tuple, Union

from attrs import Factory, define, has
from cattrs import Converter
from flask import Flask
from flask import Response as FrameworkResponse
from flask import request
from incant import Hook, Incanter
from werkzeug.routing import Rule

from . import BaseApp, Header
from .openapi import PYTHON_PRIMITIVES_TO_OPENAPI, MediaType, OpenAPI
from .openapi import Parameter as OpenApiParameter
from .openapi import Reference, Response, Schema, build_attrs_schema
from .openapi import converter as openapi_converter
from .path import angle_to_curly, parse_angle_path_params, strip_path_param_prefix
from .requests import get_cookie_name
from .responses import (
    dict_to_headers,
    get_status_code_results,
    identity,
    make_return_adapter,
)
from .types import is_subclass


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie():
            return request.cookies[cookie_name]

    else:

        def read_cookie():
            return request.cookies.get(cookie_name, default)

    return read_cookie


def make_flask_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Quart."""
    res = Incanter()
    res.register_hook_factory(
        lambda _: True,
        lambda p: lambda: converter.structure(
            request.args[p.name]
            if p.default is Signature.empty
            else request.args.get(p.name, p.default),
            p.annotation,
        ),
    )
    res.register_hook_factory(
        lambda p: p.annotation in (Signature.empty, str),
        lambda p: lambda: request.args[p.name]
        if p.default is Signature.empty
        else request.args.get(p.name, p.default),
    )
    res.register_hook_factory(
        lambda p: get_cookie_name(p.annotation, p.name) is not None,
        lambda p: make_cookie_dependency(get_cookie_name(p.annotation, p.name), default=p.default),  # type: ignore
    )
    return res


def framework_return_adapter(val: Tuple[Any, int, dict[str, str]]):
    return FrameworkResponse(val[0] or b"", val[1], dict_to_headers(val[2]))


@define
class App(BaseApp):
    flask: Flask = Factory(lambda: Flask(__name__))
    framework_incant: Incanter = Factory(
        lambda self: make_flask_incanter(self.converter), takes_self=True
    )

    def get(self, path, name: Optional[str] = None, flask: Optional[Flask] = None):
        return self.route(path, name=name, flask=flask)

    def post(self, path, name: Optional[str] = None, flask: Optional[Flask] = None):
        return self.route(path, name=name, flask=flask, methods=["POST"])

    def patch(self, path, name: Optional[str] = None, flask: Optional[Flask] = None):
        return self.route(path, name=name, flask=flask, methods=["PATCH"])

    def delete(self, path, name: Optional[str] = None, flask: Optional[Flask] = None):
        return self.route(path, name=name, flask=flask, methods=["DELETE"])

    def route(
        self,
        path: str,
        name: Optional[str] = None,
        flask: Optional[Flask] = None,
        methods=["GET"],
    ):
        f = flask or self.flask

        def wrapper(handler: Callable) -> Callable:
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse
            )
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            if ra is None:
                base_handler = self.base_incant.prepare(handler, is_async=False)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=False
                )

                def adapted(**kwargs):
                    return prepared(**kwargs)

            else:
                base_handler = self.base_incant.prepare(handler, is_async=False)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=False
                )
                if ra == identity:

                    def adapted(**kwargs):
                        return framework_return_adapter(prepared(**kwargs))

                else:

                    def adapted(**kwargs):
                        return framework_return_adapter(ra(prepared(**kwargs)))

            adapted.__attrsapi_handler__ = base_handler  # type: ignore

            f.route(
                path,
                methods=methods,
                endpoint=name if name is not None else handler.__name__,
            )(adapted)
            return adapted

        return wrapper

    def run(self, port: int = 8000):
        self.flask.run(port=port)

    def serve_openapi(self, path: str = "/openapi.json", flask: Optional[Flask] = None):
        openapi = make_openapi_spec(flask or self.flask)
        payload = openapi_converter.unstructure(openapi)

        async def openapi_handler() -> tuple[str, Literal[200], dict]:
            return dumps(payload), 200, {"content-type": "application/json"}

        self.route(path)(openapi_handler)

    def serve_swaggerui(self):
        from .swaggerui import swaggerui

        def swaggerui_handler() -> tuple[str, Literal[200], dict]:
            return swaggerui, 200, {"content-type": "text/html"}

        self.route("/swaggerui")(swaggerui_handler)

    def serve_redoc(self):
        from .swaggerui import redoc

        def redoc_handler() -> tuple[str, Literal[200], dict]:
            return redoc, 200, {"content-type": "text/html"}

        self.route("/redoc")(redoc_handler)


def build_operation(
    handler: Callable,
    path: str,
    components: dict[type, str],
    native_response: type,
) -> OpenAPI.PathItem.Operation:
    request_body = {}
    responses = {"200": Response(description="OK")}
    ct = "application/json"
    params = []
    if original_handler := getattr(handler, "__attrsapi_handler__", None):
        sig = signature(original_handler)
        path_params = parse_angle_path_params(path)
        meta_params: dict[str, Header] = getattr(
            original_handler, "__attrs_api_meta__", {}
        )
        for path_param in path_params:
            if path_param not in sig.parameters:
                raise Exception(f"Path parameter {path_param} not found")
            t = sig.parameters[path_param].annotation
            params.append(
                OpenApiParameter(
                    path_param,
                    OpenApiParameter.Kind.PATH,
                    True,
                    PYTHON_PRIMITIVES_TO_OPENAPI.get(t),
                )
            )

        for arg, arg_param in sig.parameters.items():
            if arg in path_params:
                continue
            elif arg_meta := meta_params.get(arg):
                if isinstance(arg_meta, Header):
                    params.append(
                        OpenApiParameter(
                            arg_meta.name,
                            OpenApiParameter.Kind.HEADER,
                            arg_param.default is Parameter.empty,
                            PYTHON_PRIMITIVES_TO_OPENAPI[str],
                        )
                    )
            else:
                arg_type = arg_param.annotation
                if cookie_name := get_cookie_name(arg_type, arg):
                    params.append(
                        OpenApiParameter(
                            cookie_name,
                            OpenApiParameter.Kind.COOKIE,
                            arg_param.default is Parameter.empty,
                            PYTHON_PRIMITIVES_TO_OPENAPI.get(
                                arg_param.annotation,
                                PYTHON_PRIMITIVES_TO_OPENAPI[str],
                            ),
                        )
                    )
                elif arg_type is not Parameter.empty and has(arg_type):
                    request_body["content"] = {
                        ct: MediaType(
                            Reference(f"#/components/schemas/{components[arg_type]}")
                        )
                    }
                else:
                    params.append(
                        OpenApiParameter(
                            arg,
                            OpenApiParameter.Kind.QUERY,
                            arg_param.default is Parameter.empty,
                            PYTHON_PRIMITIVES_TO_OPENAPI.get(
                                arg_type, PYTHON_PRIMITIVES_TO_OPENAPI[str]
                            ),
                        )
                    )

        ret_type = sig.return_annotation
        if ret_type is Parameter.empty:
            ret_type = None
        if not is_subclass(ret_type, native_response):
            statuses = get_status_code_results(ret_type)
            responses = {}
            for status_code, result_type in statuses:
                if result_type is str:
                    ct = "text/plain"
                    responses[str(status_code)] = Response(
                        "OK",
                        {ct: MediaType(PYTHON_PRIMITIVES_TO_OPENAPI[result_type])},
                    )
                elif result_type is None:
                    responses[str(status_code)] = Response("OK")
                elif has(result_type):
                    responses[str(status_code)] = Response(
                        "OK",
                        {
                            ct: MediaType(
                                Reference(
                                    f"#/components/schemas/{components[result_type]}"
                                )
                            )
                        },
                    )
                else:
                    responses[str(status_code)] = Response(
                        "OK",
                        {ct: MediaType(PYTHON_PRIMITIVES_TO_OPENAPI[result_type])},
                    )

    return OpenAPI.PathItem.Operation(responses, params)


def build_pathitem(
    path: str, path_routes: dict[str, Callable], components, native_response: type
) -> OpenAPI.PathItem:
    get = post = put = None
    if get_route := path_routes.get("get"):
        get = build_operation(get_route, path, components, native_response)
    if post_route := path_routes.get("post"):
        post = build_operation(post_route, path, components, native_response)
    if put_route := path_routes.get("put"):
        put = build_operation(put_route, path, components, native_response)
    return OpenAPI.PathItem(get=get, post=post, put=put)


def routes_to_paths(
    routes: list[tuple[Callable, Rule]],
    components: dict[type, dict[str, OpenAPI.PathItem]],
    native_response: type,
) -> dict[str, OpenAPI.PathItem]:
    res: dict[str, dict[str, Callable]] = defaultdict(dict)

    for handler, rule in routes:
        path = rule.rule
        res[path] = res[path] | {
            method.lower(): handler for method in rule.methods or set()
        }

    return {
        strip_path_param_prefix(angle_to_curly(k)): build_pathitem(
            k, v, components, native_response
        )
        for k, v in res.items()
    }


def gather_endpoint_components(
    handler: Callable, components: dict[type, str]
) -> dict[type, str]:
    original_handler = getattr(handler, "__attrsapi_handler__", None)
    if original_handler is None:
        return {}
    sig = signature(original_handler)
    for arg_param in sig.parameters.values():
        if (arg_type := arg_param.annotation) is not Parameter.empty:
            if has(arg_type) and arg_type not in components:
                name = arg_type.__name__
                counter = 0
                while name in components.values():
                    name = f"{arg_type.__name__}{counter}"
                    counter += 1
                components[arg_type] = name
    if (ret_type := sig.return_annotation) is not Parameter.empty:
        if has(ret_type) and ret_type not in components:
            name = ret_type.__name__
            counter = 0
            while name in components.values():
                name = f"{ret_type.__name__}{counter}"
                counter += 1
            components[ret_type] = name
    return components


def components_to_openapi(
    routes: list[tuple[Callable, Rule]]
) -> tuple[OpenAPI.Components, dict]:
    res: dict[str, Union[Schema, Reference]] = {}

    # First pass, we build the component registry.
    components: dict[type, str] = {}
    for handler, _ in routes:
        gather_endpoint_components(handler, components)

    for component in components:
        res[component.__name__] = build_attrs_schema(component)

    return OpenAPI.Components(res), components


def make_openapi_spec(
    app: Flask,
    title: str = "Server",
    version: str = "1.0",
    native_response_cl: type = FrameworkResponse,
) -> OpenAPI:
    url_map = app.url_map
    routes = [
        (app.view_functions[rule.endpoint], rule) for rule in url_map.iter_rules()
    ]
    c, components = components_to_openapi(routes)
    return OpenAPI(
        "3.0.3",
        OpenAPI.Info(title, version),
        routes_to_paths(routes, components, native_response_cl),
        c,
    )
