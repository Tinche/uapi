from collections import defaultdict
from inspect import Parameter, Signature, signature
from json import dumps
from typing import Any, Callable, Literal, Optional, Tuple, Union

from attrs import Factory, define, has
from cattrs import Converter
from incant import Hook, Incanter
from starlette.applications import Starlette
from starlette.requests import Request as FrameworkRequest
from starlette.responses import Response as FrameworkResponse
from starlette.routing import BaseRoute, Route

from . import BaseApp, Header
from .openapi import PYTHON_PRIMITIVES_TO_OPENAPI, MediaType, OpenAPI
from .openapi import Parameter as OpenApiParameter
from .openapi import Reference, Response, Schema, build_attrs_schema
from .openapi import converter as openapi_converter
from .path import parse_curly_path_params
from .requests import get_cookie_name
from .responses import get_status_code_results, identity, make_return_adapter
from .types import is_subclass


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie(request: FrameworkRequest):
            return request.cookies[cookie_name]

    else:

        def read_cookie(request: FrameworkRequest):
            return request.cookies.get(cookie_name, default)

    return read_cookie


def extract_cookies(headers: dict[str, str]) -> tuple[dict[str, str], list[str]]:
    h = {}
    cookies = []
    for k, v in headers.items():
        if k[:9] == "__cookie_":
            cookies.append(v)
        else:
            h[k] = v
    return h, cookies


def make_starlette_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Starlette."""
    res = Incanter()

    def query_factory(p: Parameter):
        def read_query(request: FrameworkRequest):
            return converter.structure(
                request.query_params[p.name]
                if p.default is Signature.empty
                else request.query_params.get(p.name, p.default),
                p.annotation,
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation is not FrameworkRequest,
        query_factory,
    )

    def string_query_factory(p: Parameter):
        def read_query(request: FrameworkRequest):
            return (
                request.query_params[p.name]
                if p.default is Signature.empty
                else request.query_params.get(p.name, p.default)
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation in (Signature.empty, str), string_query_factory
    )
    res.register_hook_factory(
        lambda p: get_cookie_name(p.annotation, p.name) is not None,
        lambda p: make_cookie_dependency(get_cookie_name(p.annotation, p.name), default=p.default),  # type: ignore
    )
    return res


def framework_return_adapter(val: Tuple[Any, int, dict]):
    if val[2]:
        headers, cookies = extract_cookies(val[2])
        res = FrameworkResponse(val[0] or b"", val[1], headers)
        for cookie in cookies:
            res.raw_headers.append((b"set-cookie", cookie.encode("latin1")))
        return res
    else:
        return FrameworkResponse(val[0] or b"", val[1], val[2])


@define
class App(BaseApp):
    starlette: Starlette = Factory(Starlette)
    framework_incant: Incanter = Factory(
        lambda self: make_starlette_incanter(self.converter), takes_self=True
    )

    def get(
        self, path, name: Optional[str] = None, starlette: Optional[Starlette] = None
    ):
        return self.route(path, name, starlette)

    def post(
        self, path, name: Optional[str] = None, starlette: Optional[Starlette] = None
    ):
        return self.route(path, name, starlette, methods=["POST"])

    def patch(
        self, path, name: Optional[str] = None, starlette: Optional[Starlette] = None
    ):
        return self.route(path, name, starlette, methods=["PATCH"])

    def delete(
        self, path, name: Optional[str] = None, starlette: Optional[Starlette] = None
    ):
        return self.route(path, name, starlette, methods=["DELETE"])

    def route(
        self,
        path: str,
        name: Optional[str] = None,
        starlette: Optional[Starlette] = None,
        methods=["GET"],
    ):
        s = starlette or self.starlette

        def wrapper(handler: Callable) -> Callable:
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse
            )
            path_params = parse_curly_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]
            if ra is None:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )
                sig = signature(prepared)
                path_types = {p: sig.parameters[p].annotation for p in path_params}

                async def adapted(
                    request: FrameworkRequest, _incant=self.framework_incant.aincant
                ) -> FrameworkResponse:
                    path_args = {
                        p: (
                            self.converter.structure(request.path_params[p], path_type)
                            if (path_type := path_types[p])
                            not in (str, Signature.empty)
                            else request.path_params[p]
                        )
                        for p in path_params
                    }
                    return await _incant(prepared, request=request, **path_args)

            else:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )
                sig = signature(prepared)
                path_types = {p: sig.parameters[p].annotation for p in path_params}

                if ra == identity:

                    async def adapted(
                        request: FrameworkRequest,
                        _incant=self.framework_incant.aincant,
                        _fra=framework_return_adapter,
                    ) -> FrameworkResponse:
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.path_params[p], path_type
                                )
                                if (path_type := path_types[p])
                                not in (str, Signature.empty)
                                else request.path_params[p]
                            )
                            for p in path_params
                        }
                        return _fra(
                            await _incant(prepared, request=request, **path_args)
                        )

                else:

                    async def adapted(
                        request: FrameworkRequest,
                        _incant=self.framework_incant.aincant,
                        _ra=ra,
                        _fra=framework_return_adapter,
                    ) -> FrameworkResponse:
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.path_params[p], path_type
                                )
                                if (path_type := path_types[p])
                                not in (str, Signature.empty)
                                else request.path_params[p]
                            )
                            for p in path_params
                        }
                        return _fra(
                            _ra(await _incant(prepared, request=request, **path_args))
                        )

            adapted.__attrsapi_handler__ = base_handler  # type: ignore

            s.add_route(path, adapted, name=name, methods=methods)
            return adapted

        return wrapper

    def serve_openapi(
        self, path: str = "/openapi.json", starlette: Optional[Starlette] = None
    ):
        openapi = make_openapi_spec(starlette or self.starlette)
        payload = openapi_converter.unstructure(openapi)

        async def openapi_handler() -> tuple[str, Literal[200], dict]:
            return dumps(payload), 200, {"content-type": "application/json"}

        self.route(path)(openapi_handler)

    async def run(self, port: int = 8000):
        from uvicorn import Config, Server

        config = Config(self.starlette, port=port, access_log=False)
        server = Server(config=config)
        await server.serve()


def build_operation(
    handler: Callable, path: str, components: dict[type, str]
) -> OpenAPI.PathItem.Operation:
    request_body = {}
    responses = {"200": Response(description="OK")}
    ct = "application/json"
    params = []
    if original_handler := getattr(handler, "__attrsapi_handler__", None):
        sig = signature(original_handler)
        path_params = parse_curly_path_params(path)
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
                                arg_param.annotation, PYTHON_PRIMITIVES_TO_OPENAPI[str]
                            ),
                        )
                    )

        ret_type = sig.return_annotation
        if ret_type is Parameter.empty:
            ret_type = None
        if not is_subclass(ret_type, FrameworkResponse):
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
    path: str, path_routes: dict[str, Callable], components
) -> OpenAPI.PathItem:
    get = post = put = None
    if get_route := path_routes.get("get"):
        get = build_operation(get_route, path, components)
    if post_route := path_routes.get("post"):
        post = build_operation(post_route, path, components)
    if put_route := path_routes.get("put"):
        put = build_operation(put_route, path, components)
    return OpenAPI.PathItem(get=get, post=post, put=put)


def routes_to_paths(
    routes: list[BaseRoute], components: dict[type, dict[str, OpenAPI.PathItem]]
) -> dict[str, OpenAPI.PathItem]:
    res: dict[str, dict[str, Callable]] = defaultdict(dict)

    for route_def in routes:
        if isinstance(route_def, Route):
            path = route_def.path
            res[path] = res[path] | {
                method.lower(): route_def.endpoint
                for method in route_def.methods or set()
            }

    return {k: build_pathitem(k, v, components) for k, v in res.items()}


def gather_endpoint_components(
    endpoint: Route, components: dict[type, str]
) -> dict[type, str]:
    original_handler = getattr(endpoint.endpoint, "__attrsapi_handler__", None)
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


def components_to_openapi(routes: list[BaseRoute]) -> tuple[OpenAPI.Components, dict]:
    res: dict[str, Union[Schema, Reference]] = {}

    # First pass, we build the component registry.
    components: dict[type, str] = {}
    for route_def in routes:
        if isinstance(route_def, Route):
            gather_endpoint_components(route_def, components)

    for component in components:
        res[component.__name__] = build_attrs_schema(component)

    return OpenAPI.Components(res), components


def make_openapi_spec(
    app: Starlette, title: str = "Server", version: str = "1.0"
) -> OpenAPI:
    routes = app.router.routes
    c, components = components_to_openapi(routes)
    return OpenAPI(
        "3.0.3", OpenAPI.Info(title, version), routes_to_paths(routes, components), c
    )
