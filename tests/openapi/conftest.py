import pytest

from uapi.base import App

from ..aiohttp import make_app as aiohttp_make_app
from ..django_uapi_app.views import app as django_app
from ..flask import make_app as flask_make_app
from ..quart import make_app as quart_make_app
from ..starlette import make_app as starlette_make_app


def django_make_app() -> App:
    return django_app


@pytest.fixture(
    params=[
        aiohttp_make_app,
        flask_make_app,
        quart_make_app,
        starlette_make_app,
        django_make_app,
    ],
    ids=["aiohttp", "flask", "quart", "starlette", "django"],
)
def app(request) -> App:
    return request.param()
