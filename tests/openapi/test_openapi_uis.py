from asyncio import TaskGroup
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
    app.serve_swaggerui(openapi_path="/openapi_test.json")
    app.serve_redoc(openapi_path="/openapi_test.json")
    app.serve_elements(openapi_path="/openapi_test.json")

    async with TaskGroup() as tg:
        t = tg.create_task(run_on_flask(app, unused_tcp_port))
        yield unused_tcp_port

        t.cancel()


@pytest.mark.asyncio(loop_scope="session")
async def test_elements(openapi_renderer_app: int) -> None:
    async with ClientSession() as session:
        resp = await session.get(f"http://localhost:{openapi_renderer_app}/elements")

        assert resp.status == 200
        assert 'apiDescriptionUrl="/openapi_test.json"' in (await resp.text())


@pytest.mark.asyncio(loop_scope="session")
async def test_swagger(openapi_renderer_app: int) -> None:
    """SwaggerUI is served properly."""
    async with ClientSession() as session:
        resp = await session.get(f"http://localhost:{openapi_renderer_app}/swaggerui")

        assert resp.status == 200
        assert 'url: "/openapi_test.json"' in (await resp.text())


@pytest.mark.asyncio(loop_scope="session")
async def test_redoc(openapi_renderer_app: int) -> None:
    """Redoc is served properly."""
    async with ClientSession() as session:
        resp = await session.get(f"http://localhost:{openapi_renderer_app}/redoc")

        assert resp.status == 200
        assert "spec-url='/openapi_test.json'" in (await resp.text())
