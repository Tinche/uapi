from __future__ import annotations

from enum import Enum, unique
from typing import Literal, Mapping, Optional, Union

from attrs import Factory, fields, frozen, has
from cattrs import override
from cattrs.gen import make_dict_unstructure_fn
from cattrs.preconf.json import make_converter

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
