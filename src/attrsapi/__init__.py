from collections import defaultdict
from collections.abc import Sequence
from inspect import getfullargspec
from re import compile
from typing import Any, Callable, get_args, get_origin

from aiohttp.web import Request, Response, RouteDef, RouteTableDef
from aiohttp.web_routedef import _Deco, _HandlerType
from attr import define, has
from cattr import structure, unstructure
from ujson import dumps, loads
from wrapt import decorator

from .openapi import build_attrs_schema

_path_pattern = compile(r"{([a-zA-Z_]+)}")


def _should_ignore(handler: _HandlerType) -> bool:
    """These handlers should be skipped."""
    fullargspec = getfullargspec(handler)
    return len(fullargspec.args) == 1 and (
        (first_arg_name := fullargspec.args[0]) not in fullargspec.annotations
        or issubclass(fullargspec.annotations[first_arg_name], Request)
    )


def parse_path_params(path_str: str) -> list[str]:
    print(path_str)
    return _path_pattern.findall(path_str)


@define
class SwattrsRouteTableDef(RouteTableDef):
    loader: Callable[[bytes, Any], Any] = lambda body, type: structure(
        loads(body), type
    )
    dumper: Callable[[Any], Response] = lambda payload: Response(
        body=dumps(unstructure(payload), escape_forward_slashes=False),
        content_type="application/json",
    )

    def __attrs_post_init__(self):
        super().__init__()

    def route(self, method: str, path: str, **kwargs: Any) -> _Deco:
        def inner(handler: _HandlerType) -> _HandlerType:
            fullargspec = getfullargspec(handler)

            # Escape hatch for just taking a request.
            if _should_ignore(handler):
                self._items.append(RouteDef(method, path, handler, kwargs))
            else:
                path_params = parse_path_params(path)
                print(path_params)
                if not len(fullargspec.args):
                    # No args, just unstructure the result.
                    @decorator
                    async def wrapper(wrapped, instance, args, kw):
                        return self.dumper(await wrapped())

                    self._items.append(RouteDef(method, path, wrapper(handler), kwargs))
                else:

                    @decorator
                    async def wrapper(wrapped, instance, args, kw):
                        return self.dumper(
                            await wrapped(
                                self.loader(
                                    await args[0].read(),
                                    fullargspec.annotations[fullargspec.args[0]],
                                )
                            )
                        )

                    self._items.append(RouteDef(method, path, wrapper(handler), kwargs))
            return handler

        return inner


def gather_endpoint_components(
    endpoint: RouteDef, components: dict[type, str]
) -> set[type]:
    if _should_ignore(endpoint.handler):
        return set()
    fullargspec = getfullargspec(endpoint.handler)
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


def build_endpoint_openapi(endpoint: RouteDef, components: dict[type, str]) -> dict:
    request_body = {}
    responses = {200: {"description": "OK"}}
    if not _should_ignore(endpoint.handler):
        fullargspec = getfullargspec(endpoint.handler)
        if len(fullargspec.args) == 1:
            arg_type = fullargspec.annotations[fullargspec.args[0]]
            request_body["content"] = {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{components[arg_type]}"}
                }
            }

        if ret_type := fullargspec.annotations.get("return"):
            print(ret_type)
            if has(ret_type):
                responses[200]["content"] = {
                    "application/json": {
                        "schema": {
                            "$ref": f"#/components/schemas/{components[ret_type]}"
                        }
                    }
                }
            elif issubclass(get_origin(ret_type), Sequence):
                args = get_args(ret_type)
                if has(args[0]):
                    responses[200]["content"] = {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "$ref": f"#/components/schemas/{components[args[0]]}",
                                },
                            }
                        }
                    }
    res = {"responses": responses}
    if request_body:
        res["requestBody"] = request_body
    return res


def routes_to_openapi(routes: RouteTableDef, components: dict[type, str]) -> dict:
    res = defaultdict(dict)

    for route_def in routes:
        if isinstance(route_def, RouteDef):
            res[route_def.path] = res[route_def.path] | {
                route_def.method.lower(): build_endpoint_openapi(route_def, components)
            }

    return res


def components_to_openapi(routes: RouteTableDef) -> dict:
    res = defaultdict(dict)

    # First pass, we build the component registry.
    components: dict[type, str] = {}
    for route_def in routes:
        if isinstance(route_def, RouteDef):
            gather_endpoint_components(route_def, components)

    for component in components:
        res[component.__name__] = build_attrs_schema(component)

    return {"schemas": res}, components


def make_openapi_spec(
    routes: RouteTableDef, title: str = "Server", version: str = "1.0"
) -> dict:
    c, components = components_to_openapi(routes)
    res = {
        "openapi": "3.0.3",
        "info": {"title": title, "version": version},
        "components": c,
        "paths": routes_to_openapi(routes, components),
    }
    return res
