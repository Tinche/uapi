from __future__ import annotations

from collections import defaultdict
from enum import Enum, unique
from inspect import Parameter as InspectParameter
from inspect import signature
from types import NoneType
from typing import Callable, Literal, Mapping, Optional, Union

from attrs import Factory, fields, frozen, has
from cattrs import override
from cattrs.gen import make_dict_unstructure_fn
from cattrs.preconf.json import make_converter

from .requests import get_cookie_name
from .responses import get_status_code_results
from .types import PathParamParser, Routes, is_subclass

converter = make_converter(omit_if_default=True)


@frozen
class Reference:
    ref: str


@frozen
class InlineType:
    type: Schema.Type


@frozen
class Schema:
    @unique
    class Type(Enum):
        OBJECT = "object"
        STRING = "string"
        INTEGER = "integer"
        NUMBER = "number"
        BOOLEAN = "boolean"
        NULL = "null"
        ARRAY = "array"

    type: Type
    properties: Optional[dict[str, AnySchema | Reference]] = None
    format: Optional[str] = None
    additionalProperties: bool | InlineType = False


@frozen
class ArraySchema:
    items: InlineType | Reference
    type: Literal[Schema.Type.ARRAY] = Schema.Type.ARRAY


@frozen
class MediaType:
    schema: Union[Reference, Schema]


@frozen
class Response:
    description: str
    content: dict[str, MediaType] = Factory(dict)


@frozen
class Parameter:
    @unique
    class Kind(str, Enum):
        QUERY = "query"
        HEADER = "header"
        PATH = "path"
        COOKIE = "cookie"

    name: str
    kind: Kind
    required: bool = False
    schema: Union[Schema, Reference, None] = None


AnySchema = Schema | ArraySchema


@frozen
class RequestBody:
    content: Mapping[str, MediaType]
    description: str | None = None
    required: bool = False


@frozen
class OpenAPI:
    @frozen
    class Info:
        title: str
        version: str

    @frozen
    class Components:
        schemas: dict[str, AnySchema | Reference]

    @frozen
    class PathItem:
        @frozen
        class Operation:
            responses: dict[str, Response]
            parameters: list[Parameter] = Factory(list)
            requestBody: RequestBody | None = None

        get: Optional[Operation] = None
        post: Optional[Operation] = None
        put: Optional[Operation] = None
        patch: Optional[Operation] = None
        delete: Optional[Operation] = None

    @frozen
    class Path:
        pass

    openapi: str
    info: Info
    paths: dict[str, PathItem]
    components: Components


PYTHON_PRIMITIVES_TO_OPENAPI = {
    str: Schema(Schema.Type.STRING),
    int: Schema(Schema.Type.INTEGER),
    bool: Schema(Schema.Type.BOOLEAN),
    float: Schema(Schema.Type.NUMBER, format="double"),
    bytes: Schema(Schema.Type.STRING, format="binary"),
}


def build_operation(
    handler: Callable,
    path: str,
    components: dict[type, str],
    path_param_parser: PathParamParser,
    framework_resp_cls: type | None,
) -> OpenAPI.PathItem.Operation:
    request_bodies = {}
    request_body_required = False
    responses = {"200": Response(description="OK")}
    ct = "application/json"
    params = []
    sig = signature(handler)
    path_params = path_param_parser(path)[1]
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
        else:
            arg_type = arg_param.annotation
            if cookie_name := get_cookie_name(arg_type, arg):
                params.append(
                    Parameter(
                        cookie_name,
                        Parameter.Kind.COOKIE,
                        arg_param.default is InspectParameter.empty,
                        PYTHON_PRIMITIVES_TO_OPENAPI.get(
                            arg_param.annotation, PYTHON_PRIMITIVES_TO_OPENAPI[str]
                        ),
                    )
                )
            elif arg_type is not InspectParameter.empty and has(arg_type):
                request_bodies[ct] = MediaType(
                    Reference(f"#/components/schemas/{components[arg_type]}")
                )
                request_body_required = arg_param.default is InspectParameter.empty
            else:
                params.append(
                    Parameter(
                        arg,
                        Parameter.Kind.QUERY,
                        arg_param.default is InspectParameter.empty,
                        PYTHON_PRIMITIVES_TO_OPENAPI.get(
                            arg_param.annotation, PYTHON_PRIMITIVES_TO_OPENAPI[str]
                        ),
                    )
                )

    ret_type = sig.return_annotation
    if ret_type is InspectParameter.empty:
        ret_type = None
    if framework_resp_cls is None or not is_subclass(ret_type, framework_resp_cls):
        statuses = get_status_code_results(ret_type)
        responses = {}
        for status_code, result_type in statuses:
            if result_type is str:
                ct = "text/plain"
                responses[str(status_code)] = Response(
                    "OK", {ct: MediaType(PYTHON_PRIMITIVES_TO_OPENAPI[result_type])}
                )
            elif result_type in (None, NoneType):
                responses[str(status_code)] = Response("OK")
            elif has(result_type):
                responses[str(status_code)] = Response(
                    "OK",
                    {
                        ct: MediaType(
                            Reference(f"#/components/schemas/{components[result_type]}")
                        )
                    },
                )
            else:
                responses[str(status_code)] = Response(
                    "OK", {ct: MediaType(PYTHON_PRIMITIVES_TO_OPENAPI[result_type])}
                )
    req_body = None
    if request_bodies:
        req_body = RequestBody(request_bodies, required=request_body_required)
    return OpenAPI.PathItem.Operation(responses, params, req_body)


def build_pathitem(
    path: str,
    path_routes: dict[str, Callable],
    components,
    path_param_parser: PathParamParser,
    framework_resp_cls: type | None,
) -> OpenAPI.PathItem:
    get = post = put = patch = delete = None
    if get_route := path_routes.get("GET"):
        get = build_operation(
            get_route, path, components, path_param_parser, framework_resp_cls
        )
    if post_route := path_routes.get("POST"):
        post = build_operation(
            post_route, path, components, path_param_parser, framework_resp_cls
        )
    if put_route := path_routes.get("PUT"):
        put = build_operation(
            put_route, path, components, path_param_parser, framework_resp_cls
        )
    if patch_route := path_routes.get("PATCH"):
        patch = build_operation(
            patch_route, path, components, path_param_parser, framework_resp_cls
        )
    if delete_route := path_routes.get("DELETE"):
        delete = build_operation(
            delete_route, path, components, path_param_parser, framework_resp_cls
        )
    return OpenAPI.PathItem(get, post, put, patch, delete)


def routes_to_paths(
    routes: Routes,
    components: dict[type, dict[str, OpenAPI.PathItem]],
    path_param_parser: PathParamParser,
    framework_resp_cls: type | None = None,
) -> dict[str, OpenAPI.PathItem]:
    res: dict[str, dict[str, Callable]] = defaultdict(dict)

    for (method, path), (handler, _) in routes.items():
        path = path_param_parser(path)[0]
        res[path] = res[path] | {method: handler}

    return {
        k: build_pathitem(k, v, components, path_param_parser, framework_resp_cls)
        for k, v in res.items()
    }


def gather_endpoint_components(
    handler: Callable, components: dict[type, str]
) -> dict[type, str]:
    sig = signature(handler)
    for arg in sig.parameters.values():
        if arg.annotation is not InspectParameter.empty:
            arg_type = arg.annotation
            if has(arg_type) and arg_type not in components:
                name = arg_type.__name__
                counter = 0
                while name in components.values():
                    name = f"{arg_type.__name__}{counter}"
                    counter += 1
                components[arg_type] = name
    if (ret_type := sig.return_annotation) is not InspectParameter.empty:
        for _, r in get_status_code_results(ret_type):
            if has(r) and r not in components:
                name = r.__name__
                counter = 0
                while name in components.values():
                    name = f"{r.__name__}{counter}"
                    counter += 1
                components[r] = name
    return components


def components_to_openapi(routes: Routes) -> tuple[OpenAPI.Components, dict]:
    """Build the components part.

    Components are complex structures, like classes, as opposed to primitives like ints.
    """
    # First pass, we build the component registry.
    components: dict[type, str] = {}
    for handler, _ in routes.values():
        gather_endpoint_components(handler, components)

    res: dict[str, AnySchema | Reference] = {}
    for component in components:
        build_attrs_schema(component, res)

    return OpenAPI.Components(res), components


def make_openapi_spec(
    routes: Routes,
    path_param_parser: PathParamParser,
    title: str = "Server",
    version: str = "1.0",
    framework_resp_cls: type | None = None,
) -> OpenAPI:
    c, components = components_to_openapi(routes)
    return OpenAPI(
        "3.0.3",
        OpenAPI.Info(title, version),
        routes_to_paths(routes, components, path_param_parser, framework_resp_cls),
        c,
    )


def build_attrs_schema(type: type, res: dict[str, AnySchema | Reference]):
    properties = {}
    for a in fields(type):
        if a.type is None:
            continue
        if a.type in PYTHON_PRIMITIVES_TO_OPENAPI:
            schema: AnySchema | Reference = PYTHON_PRIMITIVES_TO_OPENAPI[a.type]
        elif has(a.type):
            ref = f"#/components/schemas/{a.type.__name__}"
            if ref not in res:
                build_attrs_schema(a.type, res)
            schema = Reference(ref)
        elif getattr(a.type, "__origin__", None) is list:
            arg = a.type.__args__[0]
            if has(arg):
                ref = f"#/components/schemas/{arg.__name__}"
                if ref not in res:
                    build_attrs_schema(arg, res)
                schema = ArraySchema(Reference(ref))
        elif getattr(a.type, "__origin__", None) is dict:
            val_arg = a.type.__args__[1]
            schema = Schema(
                Schema.Type.OBJECT,
                additionalProperties=InlineType(
                    PYTHON_PRIMITIVES_TO_OPENAPI[val_arg].type
                ),
            )
        else:
            continue
        properties[a.name] = schema

    res[type.__name__] = Schema(type=Schema.Type.OBJECT, properties=properties)


converter.register_unstructure_hook(
    Reference,
    make_dict_unstructure_fn(Reference, converter, ref=override(rename="$ref")),
)
converter.register_unstructure_hook(
    Parameter,
    make_dict_unstructure_fn(
        Parameter, converter, omit_if_default=True, kind=override(rename="in")
    ),
)
