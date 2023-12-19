"""Internal OpenAPI functionality."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from inspect import Parameter as InspectParameter
from inspect import signature
from types import NoneType
from typing import Any, TypeAlias, get_args

from attrs import has
from cattrs._compat import is_union_type
from incant import is_subclass

from .openapi import (
    AnySchema,
    ApiKeySecurityScheme,
    ArraySchema,
    IntegerSchema,
    MediaType,
    MediaTypeName,
    OneOfSchema,
    OpenAPI,
    Parameter,
    Reference,
    RequestBody,
    Response,
    Schema,
    SchemaBuilder,
    SecurityRequirement,
    StatusCodeType,
)
from .requests import (
    get_cookie_name,
    maybe_form_type,
    maybe_header_type,
    maybe_req_body_type,
)
from .shorthands import ResponseShorthand, can_shorthand_handle
from .status import BaseResponse, get_status_code
from .types import Method, PathParamParser, RouteName, RouteTags

Routes: TypeAlias = dict[
    tuple[Method, str], tuple[Callable, Callable, RouteName, RouteTags]
]
SummaryTransformer: TypeAlias = Callable[[Callable, str], str | None]
DescriptionTransformer: TypeAlias = Callable[[Callable, str], str | None]


def default_summary_transformer(handler: Callable, name: str) -> str:
    return name.replace("_", " ").title()


def default_description_transformer(handler: Callable, name: str) -> str | None:
    """Use the handler docstring, if present."""
    return getattr(handler, "__doc__", None)


def build_operation(
    handler: Callable,
    original_handler: Callable,
    name: str,
    path: str,
    builder: SchemaBuilder,
    path_param_parser: PathParamParser,
    framework_req_cls: type | None,
    framework_resp_cls: type | None,
    shorthands: Iterable[type[ResponseShorthand]],
    security_schemas: Mapping[str, ApiKeySecurityScheme],
    summary_transformer: SummaryTransformer,
    description_transformer: DescriptionTransformer,
    tags: list[str],
) -> OpenAPI.PathItem.Operation:
    """Convert a route into an operation."""
    request_bodies = {}
    request_body_required = False
    responses: dict[StatusCodeType, Response] = {"200": Response(description="OK")}
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
                builder.PYTHON_PRIMITIVES_TO_OPENAPI.get(t),
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
                    builder.PYTHON_PRIMITIVES_TO_OPENAPI.get(
                        header_type, builder.PYTHON_PRIMITIVES_TO_OPENAPI[str]
                    ),
                )
            )
        elif cookie_name := get_cookie_name(arg_type, arg):
            params.append(
                Parameter(
                    cookie_name,
                    Parameter.Kind.COOKIE,
                    arg_param.default is InspectParameter.empty,
                    builder.PYTHON_PRIMITIVES_TO_OPENAPI.get(
                        arg_param.annotation, builder.PYTHON_PRIMITIVES_TO_OPENAPI[str]
                    ),
                )
            )
        elif arg_type is not InspectParameter.empty and (
            type_and_loader := maybe_req_body_type(arg_param)
        ):
            req_type, loader = type_and_loader
            if has(req_type):
                request_bodies[loader.content_type or "*/*"] = MediaType(
                    builder.get_schema_for_type(req_type)
                )
            else:
                # It's a dict.
                v_type = req_type.__args__[1]  # type: ignore[attr-defined]

                add_prop = builder.get_schema_for_type(v_type)

                if isinstance(add_prop, ArraySchema):
                    raise Exception("Arrayschema not supported.")

                request_bodies[loader.content_type or "*/*"] = MediaType(
                    Schema(Schema.Type.OBJECT, additionalProperties=add_prop)
                )

            request_body_required = arg_param.default is InspectParameter.empty
        elif arg_type is not InspectParameter.empty and (
            form_type := maybe_form_type(arg_param)
        ):
            # A body form.
            request_bodies["application/x-www-form-urlencoded"] = MediaType(
                builder.get_schema_for_type(form_type)
            )
        else:
            if is_union_type(arg_type):
                refs: list[Reference | Schema | IntegerSchema] = []
                for union_member in arg_type.__args__:
                    if union_member is NoneType:
                        refs.append(Schema(Schema.Type.NULL))
                    elif union_member in builder.PYTHON_PRIMITIVES_TO_OPENAPI:
                        refs.append(builder.PYTHON_PRIMITIVES_TO_OPENAPI[union_member])
                param_schema: OneOfSchema | Schema | IntegerSchema = OneOfSchema(refs)
            else:
                param_schema = builder.PYTHON_PRIMITIVES_TO_OPENAPI.get(
                    arg_param.annotation, builder.PYTHON_PRIMITIVES_TO_OPENAPI[str]
                )
            params.append(
                Parameter(
                    arg,
                    Parameter.Kind.QUERY,
                    arg_param.default is InspectParameter.empty,
                    param_schema,
                )
            )

    ret_type = sig.return_annotation
    if ret_type is InspectParameter.empty:
        ret_type = None
    if framework_resp_cls is None or not is_subclass(ret_type, framework_resp_cls):
        statuses = get_status_code_results(ret_type)
        responses = {}
        for status_code, result_type in statuses:
            rs = []
            rts = (
                [result_type]
                if not is_union_type(result_type)
                else get_args(result_type)
            )
            for rt in rts:
                for shorthand in shorthands:
                    if can_shorthand_handle(rt, shorthand):
                        shorthand_resp = shorthand.make_openapi_response(rt, builder)
                        if shorthand_resp is not None:
                            rs.append(shorthand_resp)
                        break
                if rs:
                    responses[str(status_code)] = _coalesce_responses(rs)
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


def _coalesce_responses(rs: Sequence[Response]) -> Response:
    first_resp = rs[0]
    content: dict[MediaTypeName, list[AnySchema | Reference]] = {}
    for r in rs:
        for mtn, mt in r.content.items():
            if isinstance(mt.schema, OneOfSchema):
                content.setdefault(mtn, []).extend(mt.schema.oneOf)
            else:
                content.setdefault(mtn, []).append(mt.schema)

    return Response(
        first_resp.description,
        {
            k: MediaType(v[0]) if len(v) == 1 else MediaType(OneOfSchema(v))
            for k, v in content.items()
        },
    )


def build_pathitem(
    path: str,
    path_routes: dict[Method, tuple[Callable, Callable, RouteName, RouteTags]],
    builder: SchemaBuilder,
    path_param_parser: PathParamParser,
    framework_req_cls: type | None,
    framework_resp_cls: type | None,
    shorthands: Iterable[type[ResponseShorthand]],
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
            builder,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            shorthands,
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
            builder,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            shorthands,
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
            builder,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            shorthands,
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
            builder,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            shorthands,
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
            builder,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            shorthands,
            security_schemas,
            summary_transformer,
            description_transformer,
            list(delete_route[3]),
        )
    return OpenAPI.PathItem(get, post, put, patch, delete)


def routes_to_paths(
    routes: Routes,
    builder: SchemaBuilder,
    path_param_parser: PathParamParser,
    framework_req_cls: type | None,
    framework_resp_cls: type | None,
    shorthands: Iterable[type[ResponseShorthand]],
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
            builder,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            shorthands,
            security_schemas,
            summary_transformer,
            description_transformer,
        )
        for k, v in res.items()
    }


def gather_endpoint_components(handler: Callable, builder: SchemaBuilder) -> None:
    sig = signature(handler, eval_str=True)
    for arg in sig.parameters.values():
        if (
            arg.annotation is not InspectParameter.empty
            and (type_and_loader := maybe_req_body_type(arg)) is not None
            and (arg_type := type_and_loader[0]) not in builder.names
        ):
            if has(arg_type):
                builder.get_schema_for_type(arg_type)
            else:
                # It's a dict.
                val_arg = arg_type.__args__[1]  # type: ignore[attr-defined]
                if has(val_arg):
                    builder.get_schema_for_type(val_arg)
        elif arg.annotation is not InspectParameter.empty and (
            form_type := maybe_form_type(arg)
        ):
            builder.get_schema_for_type(form_type)


def components_to_openapi(
    routes: Routes,
    builder: SchemaBuilder,
    security_schemes: dict[str, ApiKeySecurityScheme] = {},
) -> OpenAPI.Components:
    """Build the components part.

    Components are complex structures, like classes, as opposed to primitives like ints.
    """
    # First pass, we build the component registry.
    for handler, *_ in routes.values():
        gather_endpoint_components(handler, builder)

    for component in builder._build_queue:
        builder.get_schema_for_type(component)

    return OpenAPI.Components(builder.components, security_schemes)


def make_openapi_spec(
    routes: Routes,
    path_param_parser: PathParamParser,
    title: str = "Server",
    version: str = "1.0",
    framework_req_cls: type | None = None,
    framework_resp_cls: type | None = None,
    shorthands: Iterable[type[ResponseShorthand]] = [],
    security_schemes: list[ApiKeySecurityScheme] = [],
    summary_transformer: SummaryTransformer = default_summary_transformer,
    description_transformer: DescriptionTransformer = default_description_transformer,
) -> OpenAPI:
    schema_builder = SchemaBuilder()
    c = components_to_openapi(
        routes,
        schema_builder,
        {f"{scheme.in_}/{scheme.name}": scheme for scheme in security_schemes},
    )
    res = OpenAPI(
        "3.0.3",
        OpenAPI.Info(title, version),
        routes_to_paths(
            routes,
            schema_builder,
            path_param_parser,
            framework_req_cls,
            framework_resp_cls,
            shorthands,
            c.securitySchemes,
            summary_transformer,
            description_transformer,
        ),
        c,
    )
    while schema_builder._build_queue:
        for component in list(schema_builder._build_queue):
            schema_builder.build_schema_from_rules(component)
    return res


def return_type_to_statuses(t: type) -> dict[int, Any]:
    per_status: dict[int, Any] = {}
    for typ in get_args(t) if is_union_type(t) else [t]:
        if is_subclass(typ, BaseResponse) or is_subclass(
            getattr(typ, "__origin__", None), BaseResponse
        ):
            if hasattr(typ, "__origin__"):
                status = get_status_code(typ.__origin__)
                typ = typ.__args__[0]
            else:
                status = get_status_code(typ)
                typ = type(None)
        elif typ in (None, NoneType):
            status = 204
        else:
            status = 200
        if status in per_status:
            per_status[status] = per_status[status] | typ
        else:
            per_status[status] = typ
    return per_status


def get_status_code_results(t: type) -> list[tuple[int, Any]]:
    """Normalize a supported return type into (status code, type)."""
    return list(return_type_to_statuses(t).items())
