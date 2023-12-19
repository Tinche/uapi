# ruff: noqa: N815
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from enum import Enum, unique
from typing import Any, ClassVar, Literal, TypeAlias

from attrs import Factory, define, field, frozen, has
from cattrs import override
from cattrs._compat import get_args, is_generic, is_sequence
from cattrs.gen import make_dict_structure_fn, make_dict_unstructure_fn
from cattrs.preconf.json import make_converter

converter = make_converter(omit_if_default=True)

# MediaTypeNames are like `application/json`.
MediaTypeName: TypeAlias = str
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
    additionalProperties: bool | Schema | IntegerSchema | Reference = False
    enum: list[str] | None = None
    required: list[str] = Factory(list)


@frozen
class IntegerSchema:
    format: Literal[None, "int32", "int64"] = None
    minimum: int | None = None
    maximum: int | None = None
    exclusiveMinimum: bool = False
    exclusiveMaximum: bool = False
    multipleOf: int | None = None
    enum: list[int] = Factory(list)
    type: Literal[Schema.Type.INTEGER] = Schema.Type.INTEGER


@frozen
class ArraySchema:
    items: Schema | IntegerSchema | Reference
    type: Literal[Schema.Type.ARRAY] = Schema.Type.ARRAY


@frozen
class OneOfSchema:
    oneOf: Sequence[AnySchema | Reference]


AnySchema = Schema | IntegerSchema | ArraySchema | OneOfSchema


@frozen
class MediaType:
    schema: AnySchema | Reference


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
    schema: AnySchema | Reference | None = None


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


Predicate: TypeAlias = Callable[[Any], bool]
BuildHook: TypeAlias = Callable[[Any, "SchemaBuilder"], AnySchema]


@define
class SchemaBuilder:
    """A helper builder for defining OpenAPI/JSON schemas."""

    PYTHON_PRIMITIVES_TO_OPENAPI: ClassVar[dict[type, Schema | IntegerSchema]] = {
        str: Schema(Schema.Type.STRING),
        int: IntegerSchema(),
        bool: Schema(Schema.Type.BOOLEAN),
        float: Schema(Schema.Type.NUMBER, format="double"),
        bytes: Schema(Schema.Type.STRING, format="binary"),
        date: Schema(Schema.Type.STRING, format="date"),
        datetime: Schema(Schema.Type.STRING, format="date-time"),
    }

    names: dict[type, str] = Factory(dict)
    components: dict[str, AnySchema | Reference] = Factory(dict)
    build_rules: list[tuple[Predicate, BuildHook]] = Factory(
        lambda self: self.default_build_rules(), takes_self=True
    )
    _build_queue: list[type] = field(factory=list, init=False)

    def build_schema_from_rules(self, type: Any) -> AnySchema:
        for pred, hook in self.build_rules:  # noqa: B007
            if pred(type):
                break
        else:
            raise Exception(f"Can't handle {type}")

        name = self._name_for(type)
        self.components[name] = (r := hook(type, self))
        if type in self._build_queue:
            self._build_queue.remove(type)
        return r

    def get_schema_for_type(
        self, type: Any
    ) -> Reference | Schema | IntegerSchema | ArraySchema:
        # First check inline types.
        if type in self.PYTHON_PRIMITIVES_TO_OPENAPI:
            return self.PYTHON_PRIMITIVES_TO_OPENAPI[type]
        if is_sequence(type):
            # Arrays get created inline.
            arg = get_args(type)[0]
            inner = self.get_schema_for_type(arg)
            if not isinstance(inner, ArraySchema):
                return ArraySchema(inner)
            raise Exception("Nested arrays are unsupported.")

        name = self._name_for(type)
        if name not in self.components and type not in self._build_queue:
            self._build_queue.append(type)
        return Reference(f"#/components/schemas/{name}")

    def _name_for(self, type: Any) -> str:
        if type not in self.names:
            name = type.__name__ if not is_generic(type) else _make_generic_name(type)
            counter = 2
            while name in self.names.values():
                name = f"{type.__name__}{counter}"
                counter += 1
            self.names[type] = name
        return self.names[type]

    @classmethod
    def default_build_rules(cls) -> list[tuple[Predicate, BuildHook]]:
        """Set up the default build rules."""
        from .attrschema import build_attrs_schema

        return [
            (
                cls.PYTHON_PRIMITIVES_TO_OPENAPI.__contains__,
                lambda t, _: cls.PYTHON_PRIMITIVES_TO_OPENAPI[t],
            ),
            (has, build_attrs_schema),
        ]


def _make_generic_name(type: type) -> str:
    """Used for generic attrs classes (Generic[int] instead of just Generic)."""
    return type.__name__ + "[" + ", ".join(t.__name__ for t in type.__args__) + "]"  # type: ignore


def _structure_schemas(val, _):
    if "$ref" in val:
        return converter.structure(val, Reference)
    if "oneOf" in val:
        return converter.structure(val, OneOfSchema)

    type = Schema.Type(val["type"])
    if type is Schema.Type.ARRAY:
        return converter.structure(val, ArraySchema)
    if type is Schema.Type.INTEGER:
        return converter.structure(val, IntegerSchema)
    return converter.structure(val, Schema)


def _structure_schema_or_ref(val, _) -> Schema | IntegerSchema | Reference:
    if "$ref" in val:
        return converter.structure(val, Reference)
    type = Schema.Type(val["type"])
    if type is Schema.Type.INTEGER:
        return converter.structure(val, IntegerSchema)
    return converter.structure(val, Schema)


converter.register_structure_hook(AnySchema | Reference, _structure_schemas)
converter.register_structure_hook(
    Schema | IntegerSchema | Reference, _structure_schema_or_ref
)
converter.register_structure_hook(
    Schema | ArraySchema | Reference,
    lambda v, _: converter.structure(v, Reference)
    if "$ref" in v
    else (
        converter.structure(v, ArraySchema)
        if "items" in v
        else converter.structure(v, Schema)
    ),
)
converter.register_structure_hook(
    bool | Schema | IntegerSchema | Reference,
    lambda v, _: v
    if isinstance(v, bool)
    else (
        converter.structure(v, Reference)
        if "$ref" in v
        else (
            converter.structure(v, IntegerSchema)
            if v["type"] == "integer"
            else converter.structure(v, Schema)
        )
    ),
)
converter.register_structure_hook(
    Parameter, make_dict_structure_fn(Parameter, converter, kind=override(rename="in"))
)
converter.register_structure_hook(
    Reference, make_dict_structure_fn(Reference, converter, ref=override(rename="$ref"))
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
converter.register_unstructure_hook(
    IntegerSchema,
    make_dict_unstructure_fn(
        IntegerSchema, converter, type=override(omit_if_default=False)
    ),
)
