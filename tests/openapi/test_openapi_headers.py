"""Test headers."""
from uapi.openapi import OpenAPI, Parameter, Schema

from ..django_uapi_app.views import App


def test_header(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/header"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is not None
    assert op.delete is None

    assert op.put.parameters == [
        Parameter(
            "test-header",
            Parameter.Kind.HEADER,
            required=True,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert op.put.responses["200"]
    schema = op.put.responses["200"].content["text/plain"].schema
    assert isinstance(schema, Schema)
    assert schema.type == Schema.Type.STRING


def test_default_header(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/header-default"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is not None
    assert op.delete is None

    assert op.put.parameters == [
        Parameter(
            "test-header",
            Parameter.Kind.HEADER,
            required=False,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert op.put.responses["200"]
    schema = op.put.responses["200"].content["text/plain"].schema
    assert isinstance(schema, Schema)
    assert schema.type == Schema.Type.STRING
