# ruff: noqa: N815
from __future__ import annotations

from collections.abc import Mapping, Sequence
from enum import Enum, unique
from typing import Literal, TypeAlias

from attrs import Factory, frozen
from cattrs import override
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn
from cattrs.preconf.json import make_converter

converter = make_converter(omit_if_default=True)

# MediaTypeNames are like `application/json`.
MediaTypeName = str
# HTTP status codes
StatusCodeType: TypeAlias = str


@frozen
class Reference:
    ref: str


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
    items: Schema | Reference
    type: Literal[Schema.Type.ARRAY] = Schema.Type.ARRAY


@frozen
class OneOfSchema:
    oneOf: Sequence[Reference | Schema]


@frozen
class MediaType:
    schema: Schema | OneOfSchema | ArraySchema | Reference


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
    return converter.structure(val, Schema if "type" in val else Reference)


converter.register_structure_hook(
    Schema | OneOfSchema | ArraySchema | Reference, structure_schemas
)
converter.register_structure_hook(Schema | Reference, structure_inlinetype_ref)
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
