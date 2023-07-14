import contextlib
from asyncio import CancelledError, create_task, sleep
from collections.abc import Callable
from datetime import timedelta

import pytest
from aioredis import create_redis_pool
from httpx import AsyncClient

from tests.aiohttp import run_on_aiohttp
from uapi.aiohttp import App as AiohttpApp
from uapi.cookies import CookieSettings
from uapi.openapi import ApiKeySecurityScheme
from uapi.sessions.redis import AsyncSession, configure_async_sessions
from uapi.status import Created, NoContent


async def configure_redis_session_app(app: AiohttpApp) -> None:
    configure_async_sessions(
        app,
        await create_redis_pool("redis://"),
        cookie_settings=CookieSettings(secure=False),
        max_age=timedelta(seconds=1),
    )

    @app.get("/")
    async def index(session: AsyncSession) -> str:
        if "user_id" not in session:
            return "naughty!"
        return session["user_id"]

    @app.post("/login")
    async def login(username: str, session: AsyncSession) -> Created[None]:
        session["user_id"] = username
        return Created(None, await session.update_session(namespace=username))

    @app.post("/logout")
    async def logout(session: AsyncSession) -> NoContent:
        return NoContent(await session.clear_session())


@pytest.fixture(scope="session")
async def redis_session_app(unused_tcp_port_factory: Callable[..., int]):
    unused_tcp_port = unused_tcp_port_factory()
    app = AiohttpApp()
    await configure_redis_session_app(app)
    app.serve_openapi()
    t = create_task(run_on_aiohttp(app, unused_tcp_port))
    yield unused_tcp_port
    t.cancel()
    with contextlib.suppress(CancelledError):
        await t


async def test_login_logout(redis_session_app: int):
    """Test path parameter handling."""
    username = "MyCoolUsername"
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{redis_session_app}/")
        assert resp.text == "naughty!"

        resp = await client.post(
            f"http://localhost:{redis_session_app}/login", params={"username": username}
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{redis_session_app}/")
        assert resp.text == "MyCoolUsername"

        async with AsyncClient() as new_client:
            resp = await new_client.get(f"http://localhost:{redis_session_app}/")
            assert resp.text == "naughty!"

        resp = await client.get(f"http://localhost:{redis_session_app}/")
        assert resp.text == "MyCoolUsername"

        resp = await client.post(f"http://localhost:{redis_session_app}/logout")
        assert resp.text == ""
        assert resp.status_code == 204
        assert not resp.cookies

        resp = await client.get(f"http://localhost:{redis_session_app}/")
        assert resp.text == "naughty!"


async def test_session_expiry(redis_session_app: int) -> None:
    """Test path parameter handling."""
    username = "MyCoolUsername"
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{redis_session_app}/")
        assert resp.text == "naughty!"

        resp = await client.post(
            f"http://localhost:{redis_session_app}/login", params={"username": username}
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{redis_session_app}/")
        assert resp.text == "MyCoolUsername"

        await sleep(2)

        resp = await client.get(f"http://localhost:{redis_session_app}/")
        assert resp.text == "naughty!"


async def test_openapi_security() -> None:
    app = AiohttpApp()
    await configure_redis_session_app(app)

    openapi = app.make_openapi_spec()

    assert openapi.components.securitySchemes[
        "cookie/session_id"
    ] == ApiKeySecurityScheme("session_id", "cookie")

    assert openapi.paths["/"].get
    assert openapi.paths["/"].get.security == [{"cookie/session_id": []}]

    assert openapi.paths["/logout"].post
    assert openapi.paths["/logout"].post.security == [{"cookie/session_id": []}]
