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
    """Unions of attrs classes."""
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
def test_models_same_name(app_factory) -> None:
    app: App = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        {
            "an_int": Schema(type=Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )
    assert spec.components.schemas["SimpleModel2"] == Schema(
        Schema.Type.OBJECT, {"a_different_int": Schema(type=Schema.Type.INTEGER)}
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
def test_response_models(app_factory) -> None:
    """Response models should be properly added to the spec."""
    app: App = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    assert spec.components.schemas["ResponseModel"] == Schema(
        Schema.Type.OBJECT,
        {"a_list": ArraySchema(Reference("#/components/schemas/ResponseList"))},
    )
    assert spec.components.schemas["ResponseList"] == Schema(
        Schema.Type.OBJECT, {"a": Schema(type=Schema.Type.STRING)}
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
def test_response_union_none(app_factory) -> None:
    """Response models of unions containing an inner None should be properly added to the spec."""
    app: App = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/response-union-none"]
    assert op is not None
    assert op.get is not None
    assert op.post is None
    assert op.put is None
    assert op.patch is None

    assert op.get.responses["200"]
    assert op.get.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/SimpleModel"
    )
    assert op.get.responses["403"]

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
def test_model_with_literal(app_factory) -> None:
    """Models with Literal types are properly added to the spec."""
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/literal-model"]
    assert op is not None
    assert op.get is not None
    assert op.post is None
    assert op.put is None
    assert op.delete is None
    assert op.patch is None

    assert op.get.parameters == []
    assert op.get.requestBody == RequestBody(
        {
            "application/json": MediaType(
                Reference("#/components/schemas/ModelWithLiteral")
            )
        },
        required=True,
    )

    assert spec.components.schemas["ModelWithLiteral"] == Schema(
        Schema.Type.OBJECT,
        properties={"a": Schema(Schema.Type.STRING, enum=["a", "b", "c"])},
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
def test_generic_model(app_factory) -> None:
    """Models with Literal types are properly added to the spec."""
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/generic-model"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.put is None
    assert op.delete is None
    assert op.patch is None

    assert op.post.parameters == []
    assert op.post.requestBody == RequestBody(
        {
            "application/json": MediaType(
                Reference("#/components/schemas/GenericModel[int]")
            )
        },
        required=True,
    )

    assert op.post.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/GenericModel[SimpleModel]"
    )

    assert spec.components.schemas["GenericModel[int]"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "a": Schema(Schema.Type.INTEGER),
            "b": ArraySchema(InlineType(Schema.Type.INTEGER)),
        },
    )
    assert spec.components.schemas["GenericModel[SimpleModel]"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "a": Reference("#/components/schemas/SimpleModel"),
            "b": ArraySchema(Reference("#/components/schemas/SimpleModel")),
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
