"""JSON schema for attrs."""
from types import NoneType
from typing import Any

from attrs import NOTHING, fields, has
from cattrs._compat import is_generic, is_literal, is_union_type

from .openapi import (
    AnySchema,
    ArraySchema,
    OneOfSchema,
    Reference,
    Schema,
    SchemaBuilder,
)


def _make_generic_mapping(type: type) -> dict:
    """A mapping of TypeVars to their actual bound types."""
    res = {}

    for arg, param in zip(type.__args__, type.__origin__.__parameters__, strict=True):  # type: ignore
        res[param] = arg

    return res


def build_attrs_schema(type: Any, builder: SchemaBuilder) -> Schema:
    properties = {}
    mapping = _make_generic_mapping(type) if is_generic(type) else {}
    required = []
    for a in fields(type):
        if a.type is None:
            continue

        a_type = a.type

        if a_type in mapping:
            a_type = mapping[a_type]

        if a_type in builder.PYTHON_PRIMITIVES_TO_OPENAPI:
            schema: AnySchema | Reference = builder.PYTHON_PRIMITIVES_TO_OPENAPI[a_type]
        elif has(a_type):
            schema = builder.reference_for_type(a_type)
        elif getattr(a_type, "__origin__", None) is list:
            arg = a_type.__args__[0]
            if arg in mapping:
                arg = mapping[arg]
            if has(arg):
                ref = builder.reference_for_type(arg)
                schema = ArraySchema(ref)
            elif arg in builder.PYTHON_PRIMITIVES_TO_OPENAPI:
                schema = ArraySchema(
                    Schema(builder.PYTHON_PRIMITIVES_TO_OPENAPI[arg].type)
                )
        elif getattr(a_type, "__origin__", None) is dict:
            val_arg = a_type.__args__[1]

            if has(val_arg):
                add_prop: Reference | Schema = builder.reference_for_type(val_arg)
            else:
                add_prop = builder.PYTHON_PRIMITIVES_TO_OPENAPI[val_arg]

            schema = Schema(Schema.Type.OBJECT, additionalProperties=add_prop)
        elif is_literal(a_type):
            schema = Schema(Schema.Type.STRING, enum=list(a_type.__args__))
        elif is_union_type(a_type):
            refs: list[Reference | Schema] = []
            for arg in a_type.__args__:
                if has(arg):
                    refs.append(builder.reference_for_type(arg))
                elif arg is NoneType:
                    refs.append(Schema(Schema.Type.NULL))
                elif arg in builder.PYTHON_PRIMITIVES_TO_OPENAPI:
                    refs.append(builder.PYTHON_PRIMITIVES_TO_OPENAPI[arg])
            schema = OneOfSchema(refs)
        else:
            continue
        properties[a.name] = schema
        if a.default is NOTHING:
            required.append(a.name)

    return Schema(type=Schema.Type.OBJECT, properties=properties, required=required)
