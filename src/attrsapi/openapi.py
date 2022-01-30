from enum import Enum, unique
from typing import Optional, Union

from attrs import Factory, fields, frozen
from cattrs import override
from cattrs.gen import make_dict_unstructure_fn
from cattrs.preconf.json import make_converter

converter = make_converter(omit_if_default=True)


@frozen
class Reference:
    ref: str


@frozen
class Schema:
    type: str
    items: Union["Schema", Reference, None] = None
    properties: Optional[dict[str, "Schema"]] = None
    format: Optional[str] = None


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


@frozen
class OpenAPI:
    @frozen
    class Info:
        title: str
        version: str

    @frozen
    class Components:
        schemas: dict[str, Union[Schema, Reference]]

    @frozen
    class PathItem:
        @frozen
        class Operation:
            responses: dict[str, Response]
            parameters: list[Parameter] = Factory(list)

        get: Optional[Operation] = None
        post: Optional[Operation] = None
        put: Optional[Operation] = None

    @frozen
    class Path:
        pass

    openapi: str
    info: Info
    paths: dict[str, PathItem]
    components: Components


PYTHON_PRIMITIVES_TO_OPENAPI = {
    str: Schema("string"),
    int: Schema("integer"),
    bool: Schema("boolean"),
    float: Schema("number", format="double"),
    bytes: Schema("string", format="binary"),
}


def build_attrs_schema(type: type) -> Schema:
    properties = {}
    for a in fields(type):
        if a.type in PYTHON_PRIMITIVES_TO_OPENAPI:
            schema = PYTHON_PRIMITIVES_TO_OPENAPI[a.type]
        else:
            schema = Schema("")
        properties[a.name] = schema

    return Schema(type="object", properties=properties)


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
