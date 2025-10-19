"""Test query parameters."""

from uapi.base import App
from uapi.openapi import ArraySchema, IntegerSchema, OpenAPI, Parameter, Schema


def test_get_query_int(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == [
        Parameter(
            name="page",
            kind=Parameter.Kind.QUERY,
            required=True,
            schema=IntegerSchema(),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_query_default(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query-default"]
    assert op is not None
    assert op.get
    assert op.get.parameters == [
        Parameter(
            name="page",
            kind=Parameter.Kind.QUERY,
            required=False,
            schema=IntegerSchema(),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_query_unannotated(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query/unannotated"]
    assert op is not None
    assert op.get
    assert op.get.parameters == [
        Parameter(
            name="query",
            kind=Parameter.Kind.QUERY,
            required=True,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_query_string(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query/string"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == [
        Parameter(
            name="query",
            kind=Parameter.Kind.QUERY,
            required=True,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_query_list(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query-list"]
    assert op is not None
    assert op.get
    assert op.get.parameters == [
        Parameter(
            name="param",
            kind=Parameter.Kind.QUERY,
            required=True,
            schema=ArraySchema(Schema(Schema.Type.STRING)),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]
