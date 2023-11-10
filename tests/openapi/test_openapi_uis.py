from asyncio import Event, create_task
from collections.abc import Callable

import pytest
from aiohttp import ClientSession

from uapi.flask import App

from ..flask import run_on_flask


@pytest.fixture(scope="session")
async def openapi_renderer_app(unused_tcp_port_factory: Callable[..., int]):
    unused_tcp_port = unused_tcp_port_factory()
    app = App()

    app.serve_openapi(path="/openapi_test.json")
    app.serve_elements(openapi_path="/openapi_test.json")

    shutdown_event = Event()

    t = create_task(run_on_flask(app, unused_tcp_port, shutdown_event))
    yield unused_tcp_port

    shutdown_event.set()
    await t


async def test_elements(openapi_renderer_app: int) -> None:
    async with ClientSession() as session:
        resp = await session.get(f"http://localhost:{openapi_renderer_app}/elements")

    assert resp.status == 200
    assert 'apiDescriptionUrl="/openapi_test.json"' in (await resp.text())
