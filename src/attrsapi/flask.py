from collections import defaultdict
from inspect import Parameter, signature
from typing import Callable, Union

from attr import evolve, has
from cattr import structure, unstructure
from cattr._compat import get_args, is_sequence
from flask import Flask
from flask import Response as FlaskResponse
from flask import request
from werkzeug.routing import Rule

from . import Header
from .openapi import PYTHON_PRIMITIVES_TO_OPENAPI, MediaType, OpenAPI
from .openapi import Parameter as OpenApiParameter
from .openapi import Reference, Response, Schema, build_attrs_schema
from .path import angle_to_curly, parse_angle_path_params


def _generate_wrapper(
    handler: Callable,
    path: str,
    body_dumper=lambda p: FlaskResponse(unstructure(p)),
    path_loader=structure,
    query_loader=structure,
):
    sig = signature(handler)
    params_meta = getattr(handler, "__attrs_api_meta__", {})
    path_params = parse_angle_path_params(path)
    lines = []
    lines.append(f"def handler({', '.join(path_params)}):")

    try:
        res_is_native = (
            (ret_type := sig.return_annotation)
            and ret_type is not Parameter.empty
            and issubclass(ret_type, FlaskResponse)
        )
    except TypeError:
        res_is_native = False

    globs = {"__attrsapi_inner": handler, "__attrsapi_request": request}

    if res_is_native:
        lines.append("  return __attrsapi_inner(")
    else:
        globs["__attrsapi_dumper"] = body_dumper
        lines.append("  return __attrsapi_dumper(__attrsapi_inner(")

    for arg, arg_param in sig.parameters.items():
        if arg in path_params:
            arg_annotation = sig.parameters[arg].annotation
            if arg_annotation in (Parameter.empty, str):
                lines.append(f"    {arg},")
            else:
                lines.append(
                    f"    __attrsapi_path_loader({arg}, __attrsapi_{arg}_type),"
                )
                globs["__attrsapi_path_loader"] = path_loader
                globs[f"__attrsapi_{arg}_type"] = arg_annotation
        elif arg_meta := params_meta.get(arg):
            if isinstance(arg_meta, Header):
                # A header param.
                lines.append(f"    request.headers['{arg_meta.name}'],")
        elif (arg_type := arg_param.annotation) is not Parameter.empty and has(
            arg_type
        ):
            # defaulting to body
            pass
        else:
            # defaulting to query
            if arg_param.default is Parameter.empty:
                expr = f"__attrsapi_request.args['{arg}']"
            else:
                expr = f"__attrsapi_request.args.get('{arg}', __attrs_{arg}_default)"
                globs[f"__attrs_{arg}_default"] = arg_param.default

            if (
                arg_param.annotation is not str
                and arg_param.annotation is not Parameter.empty
            ):
                expr = f"__attrsapi_query_loader({expr}, __attrsapi_{arg}_type)"
                globs["__attrsapi_query_loader"] = query_loader
                globs[f"__attrsapi_{arg}_type"] = arg_param.annotation
            lines.append(f"    {expr},")

    lines.append("  )")
    if not res_is_native:
        lines[-1] = lines[-1] + ")"

    ls = "\n".join(lines)
    eval(compile(ls, "", "exec"), globs)

    fn = globs["handler"]

    return fn


def route(path: str, app: Flask, methods=["GET"]) -> Callable[[Callable], Callable]:
    def inner(handler: Callable) -> Callable:
        adapted = _generate_wrapper(handler, path)
        adapted.__attrsapi_handler__ = handler
        app.route(path, methods=methods, endpoint=handler.__name__)(adapted)
        return handler

    return inner


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
        meta_params = getattr(original_handler, "__attrs_api_meta__", {})
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
                if arg_type is not Parameter.empty and has(arg_type):
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

        if (
            ret_type := sig.return_annotation
        ) is not Parameter.empty and not issubclass(ret_type, native_response):
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
    path: str, path_routes: dict[str, Callable], components, native_response: type
) -> OpenAPI.PathItem:
    get = None
    if get_route := path_routes.get("get"):
        get = build_operation(get_route, path, components, native_response)
    return OpenAPI.PathItem(get=get)


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
        angle_to_curly(k): build_pathitem(k, v, components, native_response)
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
    native_response_cl: type = FlaskResponse,
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
