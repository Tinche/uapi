from collections import defaultdict
from inspect import Parameter as InspectParameter
from inspect import getfullargspec, signature
from typing import Any, Awaitable, Callable, Union, get_args

from aiohttp.web import Request as AiohttpRequest
from aiohttp.web import Response as AiohttpResponse
from aiohttp.web import RouteDef
from aiohttp.web import RouteTableDef as AiohttpRouteTableDef
from aiohttp.web_app import Application
from aiohttp.web_routedef import _Deco, _HandlerType
from aiohttp.web_urldispatcher import (
    DynamicResource,
    PlainResource,
    ResourceRoute,
    RoutesView,
    _WebHandler,
)
from attr import define, evolve, has
from cattr import structure, unstructure
from cattr._compat import is_sequence
from ujson import dumps, loads

from . import Header
from .openapi import (
    PYTHON_PRIMITIVES_TO_OPENAPI,
    MediaType,
    OpenAPI,
    Parameter,
    Reference,
    Response,
    Schema,
    build_attrs_schema,
)
from .path import parse_curly_path_params


def _should_ignore(handler: _HandlerType) -> bool:
    """These handlers should be skipped."""
    fullargspec = getfullargspec(handler)
    return (
        len(fullargspec.args) == 1
        and fullargspec.args[0] in fullargspec.annotations
        and issubclass(fullargspec.annotations[fullargspec.args[0]], AiohttpRequest)
    )


def _generate_wrapper(
    handler: Callable,
    path: str,
    body_dumper=lambda p: AiohttpResponse(body=unstructure(p)),
    path_loader=structure,
    query_loader=structure,
) -> Callable[[AiohttpRequest], Awaitable[AiohttpResponse]]:
    sig = signature(handler)
    params_meta = getattr(handler, "__attrs_api_meta__", {})
    path_params = parse_curly_path_params(path)
    lines = []
    lines.append("async def handler(request: Request):")

    globs: dict[str, Any] = {
        "inner": handler,
        "Request": AiohttpRequest,
    }

    no_result = False
    if sig.return_annotation is None:
        no_result = True
        res_is_native = False
        globs["Response"] = AiohttpResponse
    else:
        try:
            res_is_native = (
                (ret_type := sig.return_annotation)
                and ret_type is not InspectParameter.empty
                and issubclass(ret_type, AiohttpResponse)
            )
        except TypeError:
            res_is_native = False

    if no_result:
        lines.append("  await inner(")
    elif res_is_native:
        lines.append("  return await inner(")
    else:
        lines.append("  return dumper(await inner(")
        globs["dumper"] = body_dumper

    for arg, arg_param in sig.parameters.items():
        if arg in path_params:
            arg_annotation = sig.parameters[arg].annotation
            if arg_annotation in (InspectParameter.empty, str):
                lines.append(f"    request.match_info['{arg}'],")
            else:
                lines.append(
                    f"    path_loader(request.match_info['{arg}'], __{arg}_type),"
                )
                globs["path_loader"] = path_loader
                globs[f"__{arg}_type"] = arg_annotation
        elif arg_meta := params_meta.get(arg):
            if isinstance(arg_meta, Header):
                # A header param.
                lines.append(f"    request.headers['{arg_meta.name}'],")
        elif (arg_type := arg_param.annotation) is not InspectParameter.empty and has(
            arg_type
        ):
            # defaulting to body
            pass
        else:
            # defaulting to query
            if arg_param.default is InspectParameter.empty:
                expr = f"request.query['{arg}']"
            else:
                expr = f"request.query.get('{arg}', __{arg}_default)"
                globs[f"__{arg}_default"] = arg_param.default

            if (
                arg_param.annotation is not str
                and arg_param.annotation is not InspectParameter.empty
            ):
                expr = f"query_loader({expr}, __{arg}_type)"
                globs["query_loader"] = query_loader
                globs[f"__{arg}_type"] = arg_param.annotation
            lines.append(f"    {expr},")

    lines.append("  )")
    if no_result:
        lines.append("  return Response()")
    if not res_is_native and not no_result:
        lines[-1] = lines[-1] + ")"

    ls = "\n".join(lines)
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
    dumper: Callable[[Any], AiohttpResponse] = lambda payload: AiohttpResponse(
        body=dumps(unstructure(payload), escape_forward_slashes=False),
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
    handler: _WebHandler, path: str, components: dict[type, str]
) -> OpenAPI.PathItem.Operation:
    request_body = {}
    responses = {"200": Response(description="OK")}
    ct = "application/json"
    params = []
    if original_handler := getattr(handler, "__attrsapi_handler__", None):
        sig = signature(original_handler)
        path_params = parse_curly_path_params(path)
        meta_params = getattr(original_handler, "__attrs_api_meta__", {})
        for path_param in path_params:
            if path_param not in sig.parameters:
                raise Exception(f"Path parameter {path_param} not found")
            t = sig.parameters[path_param].annotation
            params.append(
                Parameter(
                    path_param,
                    Parameter.Kind.PATH,
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
                        Parameter(
                            arg_meta.name,
                            Parameter.Kind.HEADER,
                            arg_param.default is InspectParameter.empty,
                            PYTHON_PRIMITIVES_TO_OPENAPI[str],
                        )
                    )
            else:
                arg_type = arg_param.annotation
                if arg_type is not InspectParameter.empty and has(arg_type):
                    request_body["content"] = {
                        ct: MediaType(
                            Reference(f"#/components/schemas/{components[arg_type]}")
                        )
                    }
                else:
                    params.append(
                        Parameter(
                            arg,
                            Parameter.Kind.QUERY,
                            arg_param.default is InspectParameter.empty,
                            PYTHON_PRIMITIVES_TO_OPENAPI.get(
                                arg_param.annotation,
                                PYTHON_PRIMITIVES_TO_OPENAPI[str],
                            ),
                        )
                    )

        if (
            (ret_type := sig.return_annotation) is not InspectParameter.empty
            and ret_type is not None
            and not issubclass(ret_type, AiohttpResponse)
        ):
            if has(ret_type):
                responses["200"] = evolve(
                    responses["200"],
                    content={
                        ct: MediaType(
                            Reference(f"#/components/schemas/{components[ret_type]}")
                        )
                    },
                )
            elif is_sequence(ret_type):
                args = get_args(ret_type)
                if has(args[0]):
                    responses["200"] = evolve(
                        responses["200"],
                        content={
                            ct: MediaType(
                                Schema(
                                    type="array",
                                    items=Reference(
                                        f"#/components/schemas/{components[args[0]]}"
                                    ),
                                )
                            )
                        },
                    )
            else:
                responses["200"] = evolve(
                    responses["200"],
                    content={ct: MediaType(PYTHON_PRIMITIVES_TO_OPENAPI[ret_type])},
                )
    return OpenAPI.PathItem.Operation(responses, params)


def build_pathitem(
    path: str, path_routes: dict[str, _WebHandler], components
) -> OpenAPI.PathItem:
    get = post = None
    if get_route := path_routes.get("get"):
        get = build_operation(get_route, path, components)
    if post_route := path_routes.get("post"):
        post = build_operation(post_route, path, components)
    return OpenAPI.PathItem(get=get, post=post)


def routes_to_paths(
    routes: RoutesView, components: dict[type, dict[str, OpenAPI.PathItem]]
) -> dict[str, OpenAPI.PathItem]:
    res: dict[str, dict[str, _WebHandler]] = defaultdict(dict)

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
