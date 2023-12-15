"""Tests for response shorthands."""
from asyncio import create_task
from datetime import datetime, timezone
from typing import Any

import pytest
from httpx import AsyncClient

from uapi.aiohttp import AiohttpApp
from uapi.django import DjangoApp
from uapi.flask import FlaskApp
from uapi.quart import App, QuartApp
from uapi.shorthands import ResponseShorthand
from uapi.starlette import StarletteApp
from uapi.status import BaseResponse, Created, Ok

from .aiohttp import run_on_aiohttp
from .django import run_on_django
from .flask import run_on_flask
from .quart import run_on_quart
from .starlette import run_on_starlette


class DatetimeShorthand(ResponseShorthand[datetime]):
    @staticmethod
    def response_adapter(value: datetime) -> BaseResponse:
        return Created(value.isoformat())

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return isinstance(value, datetime)


@pytest.mark.parametrize(
    "app_type", [QuartApp, AiohttpApp, StarletteApp, FlaskApp, DjangoApp]
)
async def test_custom_shorthand(
    unused_tcp_port: int,
    app_type: type[QuartApp]
    | type[AiohttpApp]
    | type[StarletteApp]
    | type[FlaskApp]
    | type[DjangoApp],
) -> None:
    """Custom shorthands work."""
    app = app_type[None]().add_response_shorthand(DatetimeShorthand)  # type: ignore

    @app.get("/")
    def datetime_handler() -> datetime:
        return datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)

    if app_type is QuartApp:
        t = create_task(run_on_quart(app, unused_tcp_port))
    elif app_type is AiohttpApp:
        t = create_task(run_on_aiohttp(app, unused_tcp_port))
    elif app_type is StarletteApp:
        t = create_task(run_on_starlette(app, unused_tcp_port))
    elif app_type is FlaskApp:
        t = create_task(run_on_flask(app, unused_tcp_port))
    elif app_type is DjangoApp:
        t = create_task(run_on_django(app, unused_tcp_port))

    try:
        async with AsyncClient() as client:
            resp = await client.get(f"http://localhost:{unused_tcp_port}/")

            assert resp.status_code == 201
    finally:
        t.cancel()


async def test_shorthand_unions(unused_tcp_port) -> None:
    """Shorthands in unions work."""
    app = App()

    @app.get("/")
    async def handler(q: int = 0) -> Ok[str] | None:
        return None if not q else Ok("test")

    @app.get("/defaults")
    async def default_shorthands(q: int = 0) -> None | bytes | str:
        if not q:
            return None
        if q == 1:
            return b"bytes"
        return "text"

    t = create_task(run_on_quart(app, unused_tcp_port))

    try:
        async with AsyncClient() as client:
            resp = await client.get(f"http://localhost:{unused_tcp_port}/")
            assert resp.status_code == 204

            resp = await client.get(
                f"http://localhost:{unused_tcp_port}/", params={"q": "1"}
            )
            assert resp.status_code == 200

            resp = await client.get(f"http://localhost:{unused_tcp_port}/defaults")
            assert resp.status_code == 204

            resp = await client.get(
                f"http://localhost:{unused_tcp_port}/defaults", params={"q": 1}
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/octet-stream"
            assert await resp.aread() == b"bytes"

            resp = await client.get(
                f"http://localhost:{unused_tcp_port}/defaults", params={"q": 2}
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "text/plain"
            assert await resp.aread() == b"text"
    finally:
        t.cancel()
