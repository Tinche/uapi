"""Test the OpenAPI schema generation for attrs classes."""
import pytest

from uapi.aiohttp import make_openapi_spec as aiohttp_make_openapi_spec
from uapi.flask import make_openapi_spec as flask_make_openapi_spec
from uapi.openapi import (
    ArraySchema,
    InlineType,
    MediaType,
    OpenAPI,
    Reference,
    RequestBody,
    Schema,
)
from uapi.quart import make_openapi_spec as quart_make_openapi_spec
from uapi.starlette import make_openapi_spec as starlette_make_openapi_spec

from .aiohttp import make_app as aiohttp_make_app
from .flask import make_app as flask_make_app
from .quart import make_app as quart_make_app
from .starlette import make_app as starlette_make_app


@pytest.mark.parametrize(
    "app_factory",
    [
        (aiohttp_make_app, aiohttp_make_openapi_spec),
        (flask_make_app, flask_make_openapi_spec),
        (quart_make_app, quart_make_openapi_spec),
        (starlette_make_app, starlette_make_openapi_spec),
    ],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_model(app_factory):
    app = app_factory[0]()
    spec: OpenAPI = app_factory[1](app)

    op = spec.paths["/get/model"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == []
    assert op.post is None
    assert op.put is None
    assert op.get.responses["200"]
    assert op.get.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/NestedModel"
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=InlineType(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


@pytest.mark.parametrize(
    "app_factory",
    [
        (aiohttp_make_app, aiohttp_make_openapi_spec),
        (flask_make_app, flask_make_openapi_spec),
        (quart_make_app, quart_make_openapi_spec),
        (starlette_make_app, starlette_make_openapi_spec),
    ],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_model_status(app_factory):
    app = app_factory[0]()
    spec: OpenAPI = app_factory[1](app)

    op = spec.paths["/get/model-status"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == []
    assert op.post is None
    assert op.put is None
    assert op.delete is None
    assert op.get.responses["201"]
    assert op.get.responses["201"].content["application/json"].schema == Reference(
        "#/components/schemas/NestedModel"
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=InlineType(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


@pytest.mark.parametrize(
    "app_factory",
    [
        (aiohttp_make_app, aiohttp_make_openapi_spec),
        (flask_make_app, flask_make_openapi_spec),
        (quart_make_app, quart_make_openapi_spec),
        (starlette_make_app, starlette_make_openapi_spec),
    ],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_post_model(app_factory):
    app = app_factory[0]()
    spec: OpenAPI = app_factory[1](app)

    op = spec.paths["/post/model"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.put is None
    assert op.delete is None

    assert op.post.parameters == []
    assert op.post.requestBody == RequestBody(
        {"application/json": MediaType(Reference("#/components/schemas/NestedModel"))},
        required=True,
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=InlineType(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )
