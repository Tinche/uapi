"""Tests for response shorthands."""
from asyncio import create_task
from datetime import UTC, datetime
from typing import Any

from httpx import AsyncClient

from uapi.quart import App
from uapi.shorthands import ResponseShorthand
from uapi.status import BaseResponse, Created

from .quart import run_on_quart


async def test_custom_shorthand(unused_tcp_port: int) -> None:
    """Custom shorthands work."""
    app = App()

    @app.get("/")
    async def datetime_handler() -> datetime:
        return datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=UTC)

    class DatetimeShorthand(ResponseShorthand[datetime]):
        @staticmethod
        def response_adapter(value: datetime) -> BaseResponse:
            return Created(value.isoformat())

        @staticmethod
        def is_union_member(value: Any) -> bool:
            return isinstance(value, datetime)

    app.add_response_shorthand(DatetimeShorthand)

    t = create_task(run_on_quart(app, unused_tcp_port))

    try:
        async with AsyncClient() as client:
            resp = await client.get(f"http://localhost:{unused_tcp_port}/")

            assert resp.status_code == 201
    finally:
        t.cancel()
