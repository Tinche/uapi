"""Test headers."""
from typing import Callable

import pytest

from uapi.openapi import OpenAPI, Parameter, Schema

from .aiohttp import make_app as aiohttp_make_app
from .django_uapi_app.views import App
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
def test_header(app_factory: Callable[[], App]) -> None:
    app = app_factory()
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
def test_default_header(app_factory: Callable[[], App]) -> None:
    app = app_factory()
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
