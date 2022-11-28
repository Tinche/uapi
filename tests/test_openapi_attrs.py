"""Test the OpenAPI schema generation for attrs classes."""
from typing import Callable

import pytest

from uapi.base import App
from uapi.openapi import (
    ArraySchema,
    InlineType,
    MediaType,
    OpenAPI,
    Reference,
    RequestBody,
    Schema,
)

from .aiohttp import make_app as aiohttp_make_app
from .django_uapi_app.views import app as django_app
from .flask import make_app as flask_make_app
from .quart import make_app as quart_make_app
from .starlette import make_app as starlette_make_app


def django_make_app() -> App:
    return django_app


@pytest.mark.parametrize(
    "app_factory",
    [
        aiohttp_make_app,
        flask_make_app,
        quart_make_app,
        starlette_make_app,
        django_make_app,
    ],
    ids=["aiohttp", "flask", "quart", "starlette", "django"],
)
def test_get_model(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

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
        aiohttp_make_app,
        flask_make_app,
        quart_make_app,
        starlette_make_app,
        django_make_app,
    ],
    ids=["aiohttp", "flask", "quart", "starlette", "django"],
)
def test_get_model_status(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

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
        aiohttp_make_app,
        flask_make_app,
        quart_make_app,
        starlette_make_app,
        django_make_app,
    ],
    ids=["aiohttp", "flask", "quart", "starlette", "django"],
)
def test_post_model(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

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


@pytest.mark.parametrize(
    "app_factory",
    [
        aiohttp_make_app,
        flask_make_app,
        quart_make_app,
        starlette_make_app,
        django_make_app,
    ],
    ids=["aiohttp", "flask", "quart", "starlette", "django"],
)
def test_patch_union(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/patch/attrs"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is None
    assert op.patch is not None
    assert op.patch.responses["200"]
    assert op.patch.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/NestedModel"
    )
    assert op.patch.responses["201"].content["application/json"].schema == Reference(
        "#/components/schemas/SimpleModel"
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
        aiohttp_make_app,
        flask_make_app,
        quart_make_app,
        starlette_make_app,
        django_make_app,
    ],
    ids=["aiohttp", "flask", "quart", "starlette", "django"],
)
def test_custom_loader(app_factory: Callable[[], App]) -> None:
    """Custom loaders advertise proper content types."""
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/custom-loader"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is not None
    assert op.delete is None

    assert op.put.parameters == []
    assert op.put.requestBody == RequestBody(
        {
            "application/vnd.uapi.v1+json": MediaType(
                Reference("#/components/schemas/NestedModel")
            )
        },
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
