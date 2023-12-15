"""Tests for response shorthands."""
from asyncio import create_task
from datetime import datetime, timezone
from typing import Any

from httpx import AsyncClient

from uapi.quart import App
from uapi.shorthands import ResponseShorthand
from uapi.status import BaseResponse, Created, Ok

from .quart import run_on_quart


class DatetimeShorthand(ResponseShorthand[datetime]):
    @staticmethod
    def response_adapter(value: datetime) -> BaseResponse:
        return Created(value.isoformat())

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return isinstance(value, datetime)


async def test_custom_shorthand(unused_tcp_port: int) -> None:
    """Custom shorthands work."""
    app = App().add_response_shorthand(DatetimeShorthand)

    @app.get("/")
    async def datetime_handler() -> datetime:
        return datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)

    t = create_task(run_on_quart(app, unused_tcp_port))

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
