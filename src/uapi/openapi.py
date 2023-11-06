# ruff: noqa: N815
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
from enum import Enum, unique
from inspect import Parameter as InspectParameter
from inspect import signature
from types import NoneType
from typing import Final, Literal, TypeAlias

from attrs import NOTHING, AttrsInstance, Factory, fields, frozen, has
from cattrs import override
from cattrs._compat import is_generic, is_literal, is_union_type
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn
from cattrs.preconf.json import make_converter

from .requests import get_cookie_name, maybe_header_type, maybe_req_body_type
from .responses import get_status_code_results
from .status import BaseResponse
from .types import Method, PathParamParser, RouteName, RouteTags, is_subclass

converter = make_converter(omit_if_default=True)

# MediaTypeNames are like `application/json`.
MediaTypeName = str
# HTTP status codes
StatusCodeType: TypeAlias = str

SummaryTransformer: TypeAlias = Callable[[Callable, str], str | None]
DescriptionTransformer: TypeAlias = Callable[[Callable, str], str | None]
Routes: TypeAlias = dict[
    tuple[Method, str], tuple[Callable, Callable, RouteName, RouteTags]
]


def default_summary_transformer(handler: Callable, name: str) -> str:
    return name.replace("_", " ").title()


def default_description_transformer(handler: Callable, name: str) -> str | None:
    """Use the handler docstring, if present."""
    return getattr(handler, "__doc__", None)


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
    properties: dict[str, AnySchema | Reference] | None = None
    format: str | None = None
    additionalProperties: bool | Schema | Reference = False
    enum: list[str] | None = None
    required: list[str] = Factory(list)


@frozen
class ArraySchema:
    items: InlineType | Reference
    type: Literal[Schema.Type.ARRAY] = Schema.Type.ARRAY


@frozen
class OneOfSchema:
    oneOf: list[Reference | InlineType]


@frozen
class MediaType:
    schema: Schema | OneOfSchema | Reference


@frozen
class Response:
    description: str
    content: dict[MediaTypeName, MediaType] = Factory(dict)


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
    schema: Schema | Reference | OneOfSchema | None = None


AnySchema = Schema | ArraySchema | OneOfSchema


@frozen
class RequestBody:
    content: Mapping[MediaTypeName, MediaType]
    description: str | None = None
    required: bool = False


@frozen
class ApiKeySecurityScheme:
    name: str
    in_: Literal["query", "header", "cookie"]
    description: str | None = None
    type: Literal["apiKey"] = "apiKey"


SecurityRequirement: TypeAlias = dict[str, list[str]]


@frozen
class OpenAPI:
    @frozen
    class Info:
        title: str
        version: str

    @frozen
    class Components:
        schemas: dict[str, AnySchema | Reference]
        securitySchemes: Mapping[str, ApiKeySecurityScheme] = Factory(dict)

    @frozen
    class PathItem:
        @frozen
        class Operation:
            responses: dict[StatusCodeType, Response]
            parameters: list[Parameter] = Factory(list)
            requestBody: RequestBody | None = None
            security: list[SecurityRequirement] = Factory(list)
            summary: str | None = None
            tags: list[str] = Factory(list)
            operationId: str | None = None
            description: str | None = None

        get: Operation | None = None
        post: Operation | None = None
        put: Operation | None = None
        patch: Operation | None = None
        delete: Operation | None = None

    @frozen
    class Path:
        pass

    openapi: str
    info: Info
    paths: dict[str, PathItem]
    components: Components


PYTHON_PRIMITIVES_TO_OPENAPI: Final = {
    str: Schema(Schema.Type.STRING),
    int: Schema(Schema.Type.INTEGER),
    bool: Schema(Schema.Type.BOOLEAN),
    float: Schema(Schema.Type.NUMBER, format="double"),
    bytes: Schema(Schema.Type.STRING, format="binary"),
}


def build_operation(
    handler: Callable,
    original_handler: Callable,
    name: str,
    path: str,
    components: dict[type, str],
    path_param_parser: PathParamParser,
    framework_req_cls: type | None,
    framework_resp_cls: type | None,
    security_schemas: Mapping[str, ApiKeySecurityScheme],
    summary_transformer: SummaryTransformer,
    description_transformer: DescriptionTransformer,
    tags: list[str],
) -> OpenAPI.PathItem.Operation:
    request_bodies = {}
    request_body_required = False
    responses = {"200": Response(description="OK")}
    params: list[Parameter] = []
    sig = signature(handler, eval_str=True)
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
        arg_type = arg_param.annotation
        if arg_type in (RouteName, Method):
            # These are special and fulfilled by uapi itself.
            continue
        if arg_type is not InspectParameter.empty and is_subclass(
            arg_type, framework_req_cls
        ):
            # We ignore params annotated as framework req classes.
            continue
        if arg_type is not InspectParameter.empty and (
            type_and_header := maybe_header_type(arg_param)
        ):
            header_type, header_spec = type_and_header
            if isinstance(header_spec.name, str):
                header_name = header_spec.name
            else:
                header_name = header_spec.name(arg)
            params.append(
                Parameter(
                    header_name,
                    Parameter.Kind.HEADER,
                    arg_param.default is InspectParameter.empty,
                    PYTHON_PRIMITIVES_TO_OPENAPI.get(
                        header_type, PYTHON_PRIMITIVES_TO_OPENAPI[str]
                    ),
                )
            )
        elif cookie_name := get_cookie_name(arg_type, arg):
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
        elif arg_type is not InspectParameter.empty and (
            type_and_loader := maybe_req_body_type(arg_param)
        ):
            req_type, loader = type_and_loader
            if has(req_type):
                request_bodies[loader.content_type or "*/*"] = MediaType(
                    Reference(f"#/components/schemas/{components[req_type]}")
                )
            else:
                # It's a dict.
                v_type = req_type.__args__[1]  # type: ignore[attr-defined]

                add_prop: Reference | Schema = (
                    Reference(f"#/components/schemas/{components[v_type]}")
                    if has(v_type)
                    else PYTHON_PRIMITIVES_TO_OPENAPI[v_type]
                )

                request_bodies[loader.content_type or "*/*"] = MediaType(
                    Schema(Schema.Type.OBJECT, additionalProperties=add_prop)
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
                responses[str(status_code)] = Response(
                    "OK",
                    {
                        "text/plain": MediaType(
                            PYTHON_PRIMITIVES_TO_OPENAPI[result_type]
                        )
                    },
                )
            elif result_type is bytes:
                responses[str(status_code)] = Response(
                    "OK",
                    {
                        "application/octet-stream": MediaType(
                            PYTHON_PRIMITIVES_TO_OPENAPI[result_type]
                        )
                    },
                )
            elif result_type in (None, NoneType):
                responses[str(status_code)] = Response("No content")
            elif has(result_type):
                responses[str(status_code)] = Response(
                    "OK",
                    {
                        "application/json": MediaType(
                            Reference(f"#/components/schemas/{components[result_type]}")
                        )
                    },
                )
            else:
                responses[str(status_code)] = Response(
                    "OK",
                    {
                        "application/json": MediaType(
                            PYTHON_PRIMITIVES_TO_OPENAPI[result_type]
                        )
                    },
                )
    req_body = None
    if request_bodies:
        req_body = RequestBody(request_bodies, required=request_body_required)

    security: list[SecurityRequirement] = []
    for sec_name, sec_scheme in security_schemas.items():
        if sec_scheme.in_ == "cookie" and any(
            p.kind is Parameter.Kind.COOKIE and p.name == sec_scheme.name
            for p in params
        ):
            security.append({sec_name: []})

    return OpenAPI.PathItem.Operation(
        responses,
        params,
        req_body,
        security,
        summary_transformer(original_handler, name),
        tags,
        name,
        description_transformer(original_handler, name),
    )


def build_pathitem(
    path: str,
    path_routes: dict[Method, tuple[Callable, Callable, RouteName, RouteTags]],
    components: dict[type, str],
    path_param_parser: PathParamParser,
    framework_req_cls: type | None,
    framework_resp_cls: type | None,
    security_schemas: Mapping[str, ApiKeySecurityScheme],
    summary_transformer: SummaryTransformer,
    description_transformer: DescriptionTransformer,
) -> OpenAPI.PathItem:
    get = post = put = patch = delete = None
    if get_route := path_routes.get("GET"):
        get = build_operation(
            get_route[0],
            get_route[1],
            get_route[2],
            path,
            components,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            security_schemas,
            summary_transformer,
            description_transformer,
            list(get_route[3]),
        )
    if post_route := path_routes.get("POST"):
        post = build_operation(
            post_route[0],
            post_route[1],
            post_route[2],
            path,
            components,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            security_schemas,
            summary_transformer,
            description_transformer,
            list(post_route[3]),
        )
    if put_route := path_routes.get("PUT"):
        put = build_operation(
            put_route[0],
            put_route[1],
            put_route[2],
            path,
            components,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            security_schemas,
            summary_transformer,
            description_transformer,
            list(put_route[3]),
        )
    if patch_route := path_routes.get("PATCH"):
        patch = build_operation(
            patch_route[0],
            patch_route[1],
            patch_route[2],
            path,
            components,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            security_schemas,
            summary_transformer,
            description_transformer,
            list(patch_route[3]),
        )
    if delete_route := path_routes.get("DELETE"):
        delete = build_operation(
            delete_route[0],
            delete_route[1],
            delete_route[2],
            path,
            components,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            security_schemas,
            summary_transformer,
            description_transformer,
            list(delete_route[3]),
        )
    return OpenAPI.PathItem(get, post, put, patch, delete)


def routes_to_paths(
    routes: Routes,
    components: dict[type, str],
    path_param_parser: PathParamParser,
    framework_req_cls: type | None,
    framework_resp_cls: type | None,
    security_schemas: Mapping[str, ApiKeySecurityScheme],
    summary_transformer: SummaryTransformer,
    description_transformer: DescriptionTransformer,
) -> dict[str, OpenAPI.PathItem]:
    res: dict[
        str, dict[Method, tuple[Callable, Callable, RouteName, RouteTags]]
    ] = defaultdict(dict)

    for (method, path), (handler, orig_handler, name, tags) in routes.items():
        path = path_param_parser(path)[0]
        res[path] = res[path] | {method: (handler, orig_handler, name, tags)}

    return {
        k: build_pathitem(
            k,
            v,
            components,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            security_schemas,
            summary_transformer,
            description_transformer,
        )
        for k, v in res.items()
    }


def _gather_attrs_components(
    type: type[AttrsInstance], components: dict[type, str]
) -> dict[type, str]:
    """DFS for attrs components."""
    if type in components:
        return components
    name = type.__name__ if not is_generic(type) else _make_generic_name(type)
    counter = 2
    while name in components.values():
        name = f"{type.__name__}{counter}"
        counter += 1
    components[type] = name
    mapping = _make_generic_mapping(type) if is_generic(type) else {}
    for a in fields(type):  # type: ignore
        if a.type is None:
            continue
        a_type = mapping.get(a.type, a.type)
        if has(a_type):
            _gather_attrs_components(a_type, components)
        elif getattr(a_type, "__origin__", None) is list:
            arg = a_type.__args__[0]
            arg = mapping.get(arg, arg)
            if has(arg):
                _gather_attrs_components(arg, components)
        elif getattr(a_type, "__origin__", None) is dict:
            val_arg = a_type.__args__[1]
            if has(val_arg):
                _gather_attrs_components(val_arg, components)
        elif is_union_type(a_type):
            for arg in a_type.__args__:
                if has(arg):
                    _gather_attrs_components(arg, components)
    return components


def _make_generic_name(type: type) -> str:
    """Used for generic attrs classes (Generic[int] instead of just Generic)."""
    return type.__name__ + "[" + ", ".join(t.__name__ for t in type.__args__) + "]"  # type: ignore


def gather_endpoint_components(
    handler: Callable, components: dict[type, str]
) -> dict[type, str]:
    sig = signature(handler, eval_str=True)
    for arg in sig.parameters.values():
        if (
            arg.annotation is not InspectParameter.empty
            and (type_and_loader := maybe_req_body_type(arg)) is not None
            and (arg_type := type_and_loader[0]) not in components
        ):
            if has(arg_type):
                if is_generic(arg_type):
                    name = _make_generic_name(arg_type)
                else:
                    name = arg_type.__name__
                counter = 0
                while name in components.values():
                    name = f"{arg_type.__name__}{counter}"
                    counter += 1
                _gather_attrs_components(arg_type, components)
            else:
                # It's a dict.
                val_arg = arg_type.__args__[1]  # type: ignore[attr-defined]
                if has(val_arg):
                    _gather_attrs_components(val_arg, components)
    if (ret_type := sig.return_annotation) is not InspectParameter.empty:
        for _, r in get_status_code_results(ret_type):
            if has(r) and not is_subclass(r, BaseResponse) and r not in components:
                _gather_attrs_components(r, components)
    return components


def components_to_openapi(
    routes: Routes, security_schemes: dict[str, ApiKeySecurityScheme] = {}
) -> tuple[OpenAPI.Components, dict[type, str]]:
    """Build the components part.

    Components are complex structures, like classes, as opposed to primitives like ints.
    """
    # First pass, we build the component registry.
    components: dict[type, str] = {}
    for handler, *_ in routes.values():
        gather_endpoint_components(handler, components)

    res: dict[str, AnySchema | Reference] = {}
    for component in components:
        _build_attrs_schema(component, components, res)

    return OpenAPI.Components(res, security_schemes), components


def make_openapi_spec(
    routes: Routes,
    path_param_parser: PathParamParser,
    title: str = "Server",
    version: str = "1.0",
    framework_req_cls: type | None = None,
    framework_resp_cls: type | None = None,
    security_schemes: list[ApiKeySecurityScheme] = [],
    summary_transformer: SummaryTransformer = default_summary_transformer,
    description_transformer: DescriptionTransformer = default_description_transformer,
) -> OpenAPI:
    c, components = components_to_openapi(
        routes, {f"{scheme.in_}/{scheme.name}": scheme for scheme in security_schemes}
    )
    return OpenAPI(
        "3.0.3",
        OpenAPI.Info(title, version),
        routes_to_paths(
            routes,
            components,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            c.securitySchemes,
            summary_transformer,
            description_transformer,
        ),
        c,
    )


def _make_generic_mapping(type: type) -> dict:
    """A mapping of TypeVars to their actual bound types."""
    res = {}

    for arg, param in zip(type.__args__, type.__origin__.__parameters__, strict=True):  # type: ignore
        res[param] = arg

    return res


def _build_attrs_schema(
    type: type[AttrsInstance],
    names: dict[type, str],
    res: dict[str, AnySchema | Reference],
) -> None:
    properties = {}
    name = names[type]
    mapping = _make_generic_mapping(type) if is_generic(type) else {}
    required = []
    for a in fields(type):  # type: ignore
        if a.type is None:
            continue

        a_type = a.type

        if a_type in mapping:
            a_type = mapping[a_type]

        if a_type in PYTHON_PRIMITIVES_TO_OPENAPI:
            schema: AnySchema | Reference = PYTHON_PRIMITIVES_TO_OPENAPI[a_type]
        elif has(a_type):
            ref = f"#/components/schemas/{names[a_type]}"
            if ref not in res:
                _build_attrs_schema(a_type, names, res)
            schema = Reference(ref)
        elif getattr(a_type, "__origin__", None) is list:
            arg = a_type.__args__[0]
            if arg in mapping:
                arg = mapping[arg]
            if has(arg):
                ref = f"#/components/schemas/{names[arg]}"
                if ref not in res:
                    _build_attrs_schema(arg, names, res)
                schema = ArraySchema(Reference(ref))
            elif arg in PYTHON_PRIMITIVES_TO_OPENAPI:
                schema = ArraySchema(InlineType(PYTHON_PRIMITIVES_TO_OPENAPI[arg].type))
        elif getattr(a_type, "__origin__", None) is dict:
            val_arg = a_type.__args__[1]

            if has(val_arg):
                ref = f"#/components/schemas/{names[val_arg]}"
                if ref not in res:
                    _build_attrs_schema(val_arg, names, res)
                add_prop: Reference | Schema = Reference(ref)
            else:
                add_prop = PYTHON_PRIMITIVES_TO_OPENAPI[val_arg]

            schema = Schema(Schema.Type.OBJECT, additionalProperties=add_prop)
        elif is_literal(a_type):
            schema = Schema(Schema.Type.STRING, enum=list(a_type.__args__))
        elif is_union_type(a_type):
            refs: list[Reference | InlineType] = []
            for arg in a_type.__args__:
                if has(arg):
                    ref = f"#/components/schemas/{names[arg]}"
                    if ref not in res:
                        _build_attrs_schema(arg, names, res)
                    refs.append(Reference(ref))
                elif arg is NoneType:
                    refs.append(InlineType(Schema.Type.NULL))
                elif arg in PYTHON_PRIMITIVES_TO_OPENAPI:
                    refs.append(InlineType(PYTHON_PRIMITIVES_TO_OPENAPI[arg].type))
            schema = OneOfSchema(refs)
        else:
            continue
        properties[a.name] = schema
        if a.default is NOTHING:
            required.append(a.name)

    res[name] = Schema(
        type=Schema.Type.OBJECT, properties=properties, required=required
    )


def structure_schemas(val, _):
    if "$ref" in val:
        return converter.structure(val, Reference)
    if "oneOf" in val:
        return converter.structure(val, OneOfSchema)

    type = Schema.Type(val["type"])
    if type is Schema.Type.ARRAY:
        return converter.structure(val, ArraySchema)
    return converter.structure(val, Schema)


def structure_inlinetype_ref(val, _):
    return converter.structure(val, InlineType if "type" in val else Reference)


converter.register_structure_hook(
    Schema | ArraySchema | OneOfSchema | Reference, structure_schemas
)
converter.register_structure_hook(InlineType | Reference, structure_inlinetype_ref)
converter.register_structure_hook(
    Parameter, make_dict_structure_fn(Parameter, converter, kind=override(rename="in"))
)
converter.register_structure_hook(
    Reference, make_dict_structure_fn(Reference, converter, ref=override(rename="$ref"))
)
converter.register_structure_hook(
    bool | Schema | Reference,
    lambda v, _: v
    if isinstance(v, bool)
    else (
        converter.structure(v, Reference)
        if "$ref" in v
        else converter.structure(v, Schema)
    ),
)
converter.register_unstructure_hook(
    ApiKeySecurityScheme,
    make_dict_unstructure_fn(
        ApiKeySecurityScheme,
        converter,
        in_=override(rename="in"),
        type=override(omit_if_default=False),
    ),
)

converter.register_unstructure_hook(
    Reference,
    make_dict_unstructure_fn(Reference, converter, ref=override(rename="$ref")),
)
converter.register_unstructure_hook(
    Parameter,
    make_dict_unstructure_fn(
        Parameter, converter, _cattrs_omit_if_default=True, kind=override(rename="in")
    ),
)
converter.register_unstructure_hook(
    ArraySchema,
    make_dict_unstructure_fn(
        ArraySchema, converter, type=override(omit_if_default=False)
    ),
)
