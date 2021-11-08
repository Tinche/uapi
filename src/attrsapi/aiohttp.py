from collections import defaultdict
from inspect import Parameter as Parameter
from inspect import getfullargspec, signature
from typing import Any, Awaitable, Callable, Union

from aiohttp.web import Request as AiohttpRequest
from aiohttp.web import Response as FrameworkResponse
from aiohttp.web import RouteDef
from aiohttp.web import RouteTableDef as AiohttpRouteTableDef
from aiohttp.web_app import Application
from aiohttp.web_routedef import _Deco, _HandlerType
from aiohttp.web_urldispatcher import (
    DynamicResource,
    Handler,
    PlainResource,
    ResourceRoute,
    RoutesView,
)
from attr import define
from cattr import structure, unstructure
from cattr._compat import has
from ujson import loads

from attrsapi.requests import get_cookie_name

from . import Header
from .openapi import PYTHON_PRIMITIVES_TO_OPENAPI, MediaType, OpenAPI
from .openapi import Parameter as OpenApiParameter
from .openapi import Reference, Response, Schema, build_attrs_schema
from .path import parse_curly_path_params
from .responses import dumps, get_status_code_results, returns_status_code
from .types import is_subclass


def _should_ignore(handler: _HandlerType) -> bool:
    """These handlers should be skipped."""
    fullargspec = getfullargspec(handler)
    return (
        len(fullargspec.args) == 1
        and fullargspec.args[0] in fullargspec.annotations
        and is_subclass(fullargspec.annotations[fullargspec.args[0]], AiohttpRequest)
    )


def _generate_wrapper(
    handler: Callable,
    path: str,
    body_dumper=lambda v: dumps(unstructure(v)),
    path_loader=structure,
    query_loader=structure,
) -> Callable[[AiohttpRequest], Awaitable[FrameworkResponse]]:
    sig = signature(handler)
    params_meta: dict[str, Header] = getattr(handler, "__attrs_api_meta__", {})
    path_params = parse_curly_path_params(path)
    lines = []
    post_lines = []
    lines.append(
        "async def handler(__attrsapi_request: Request) -> __attrsapi_Response:"
    )

    globs: dict[str, Any] = {
        "__attrsapi_inner": handler,
        "Request": AiohttpRequest,
        "__attrsapi_Response": FrameworkResponse,
    }

    if (ret_type := sig.return_annotation) in (None, Parameter.empty):
        lines.append("  __attrsapi_sc = 200")
        lines.append("  await __attrsapi_inner(")
        post_lines.append("  return __attrsapi_Response(status=__attrsapi_sc)")
    else:
        if is_subclass(ret_type, FrameworkResponse):
            # The response is native.
            lines.append("  return await __attrsapi_inner(")
        else:
            sc_results = get_status_code_results(ret_type)
            if returns_status_code(ret_type):
                lines.append(
                    "  __attrsapi_sc, __attrsapi_res = await __attrsapi_inner("
                )
            else:
                lines.append("  __attrsapi_sc = 200")
                lines.append("  __attrsapi_res = await __attrsapi_inner(")

            resp_processors = {}
            for sc, rt in sc_results:
                if rt in (bytes, str):
                    resp_processors[sc] = "__attrsapi_res", lambda r: r
                elif rt is None:
                    resp_processors[sc] = "b''", lambda r: b""
                elif has(rt):
                    resp_processors[sc] = (
                        "__attrsapi_dumper(__attrsapi_res)",
                        body_dumper,
                    )
                    globs["__attrsapi_dumper"] = body_dumper
                else:
                    raise Exception(f"Cannot handle response type {ret_type}/{rt}")

            if len({v[0] for v in resp_processors.values()}) == 1:
                body_expr = next(iter(resp_processors.values()))[0]
            else:
                body_expr = "(__attrsapi_rp[__attrsapi_sc])(__attrsapi_res)"
                globs["__attrsapi_rp"] = {k: v[1] for k, v in resp_processors.items()}

            post_lines.append(
                f"  return __attrsapi_Response(body={body_expr}, status=__attrsapi_sc)"
            )

    for arg, arg_param in sig.parameters.items():
        if arg in path_params:
            arg_annotation = sig.parameters[arg].annotation
            if arg_annotation in (Parameter.empty, str):
                lines.append(f"    __attrsapi_request.match_info['{arg}'],")
            else:
                lines.append(
                    f"    path_loader(__attrsapi_request.match_info['{arg}'], __{arg}_type),"
                )
                globs["path_loader"] = path_loader
                globs[f"__{arg}_type"] = arg_annotation
        elif arg_meta := params_meta.get(arg):
            if isinstance(arg_meta, Header):
                # A header param.
                lines.append(f"    __attrsapi_request.headers['{arg_meta.name}'],")
        elif (arg_type := arg_param.annotation) is not Parameter.empty and has(
            arg_type
        ):
            # defaulting to body
            pass
        elif cookie_name := get_cookie_name(arg_type, arg):
            if arg_param.default is Parameter.empty:
                lines.append(f"    __attrsapi_request.cookies['{cookie_name}'],")
            else:
                lines.append(
                    f"    __attrsapi_request.cookies.get('{cookie_name}', __{arg}_default),"
                )
                globs[f"__{arg}_default"] = arg_param.default
        else:
            # defaulting to query
            if arg_param.default is Parameter.empty:
                expr = f"__attrsapi_request.query['{arg}']"
            else:
                expr = f"__attrsapi_request.query.get('{arg}', __{arg}_default)"
                globs[f"__{arg}_default"] = arg_param.default

            if (
                arg_param.annotation is not str
                and arg_param.annotation is not Parameter.empty
            ):
                expr = f"query_loader({expr}, __{arg}_type)"
                globs["query_loader"] = query_loader
                globs[f"__{arg}_type"] = arg_param.annotation
            lines.append(f"    {expr},")

    lines.append("  )")

    ls = "\n".join(lines + post_lines)
    eval(compile(ls, "", "exec"), globs)

    fn = globs["handler"]

    return fn


def route(
    route_def: AiohttpRouteTableDef, method: str, path: str
) -> Callable[[Callable], Callable]:
    def inner(handler: Callable):
        fn = _generate_wrapper(handler, path)
        fn.__attrsapi_handler__ = handler  # type: ignore
        getattr(route_def, method)(path)(fn)

    return inner


@define
class RouteTableDef(AiohttpRouteTableDef):
    loader: Callable[[bytes, Any], Any] = lambda body, type: structure(
        loads(body), type
    )
    dumper: Callable[[Any], FrameworkResponse] = lambda payload: FrameworkResponse(
        body=dumps(unstructure(payload)),
        content_type="application/json",
    )
    query_loader: Callable[[str, type], Any] = structure
    path_loader: Callable[[str, type], Any] = structure

    def __attrs_post_init__(self):
        super().__init__()

    def route(self, method: str, path: str, **kwargs: Any) -> _Deco:
        def inner(handler: Callable) -> _HandlerType:
            # Escape hatch for just taking a request.
            if _should_ignore(handler):
                self._items.append(RouteDef(method, path, handler, kwargs))
            else:
                fn = _generate_wrapper(handler, path)
                fn.__attrsapi_handler__ = handler  # type: ignore

                self._items.append(RouteDef(method, path, fn, kwargs))
            return handler

        return inner


def gather_endpoint_components(
    endpoint: RouteDef, components: dict[type, str]
) -> dict[type, str]:
    original_handler = getattr(endpoint.handler, "__attrsapi_handler__", None)
    if original_handler is None:
        return {}
    fullargspec = getfullargspec(original_handler)
    for arg_name in fullargspec.args:
        if arg_name in fullargspec.annotations:
            arg_type = fullargspec.annotations[arg_name]
            if has(arg_type) and arg_type not in components:
                name = arg_type.__name__
                counter = 0
                while name in components.values():
                    name = f"{arg_type.__name__}{counter}"
                    counter += 1
                components[arg_type] = name
    if ret_type := fullargspec.annotations.get("return"):
        if has(ret_type) and ret_type not in components:
            name = ret_type.__name__
            counter = 0
            while name in components.values():
                name = f"{ret_type.__name__}{counter}"
                counter += 1
            components[ret_type] = name
    return components


def build_operation(
    handler: Handler, path: str, components: dict[type, str]
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
                                arg_param.annotation,
                                PYTHON_PRIMITIVES_TO_OPENAPI[str],
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
    path: str, path_routes: dict[str, Handler], components
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
    routes: RoutesView, components: dict[type, dict[str, OpenAPI.PathItem]]
) -> dict[str, OpenAPI.PathItem]:
    res: dict[str, dict[str, Handler]] = defaultdict(dict)

    for route_def in routes:
        if isinstance(route_def, ResourceRoute):
            resource = route_def.resource
            if resource is not None:
                if isinstance(resource, (PlainResource, DynamicResource)):
                    path = resource.canonical
                    res[path] = res[path] | {
                        route_def.method.lower(): route_def.handler
                    }

    return {k: build_pathitem(k, v, components) for k, v in res.items()}


def components_to_openapi(routes: RoutesView) -> tuple[OpenAPI.Components, dict]:
    res: dict[str, Union[Schema, Reference]] = {}

    # First pass, we build the component registry.
    components: dict[type, str] = {}
    for route_def in routes:
        if isinstance(route_def, RouteDef):
            gather_endpoint_components(route_def, components)

    for component in components:
        res[component.__name__] = build_attrs_schema(component)

    return OpenAPI.Components(res), components


def make_openapi_spec(
    app: Application, title: str = "Server", version: str = "1.0"
) -> OpenAPI:
    routes = app.router.routes()
    c, components = components_to_openapi(routes)
    return OpenAPI(
        "3.0.3", OpenAPI.Info(title, version), routes_to_paths(routes, components), c
    )
