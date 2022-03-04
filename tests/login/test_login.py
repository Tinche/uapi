from asyncio import Event, create_task, sleep
from datetime import timedelta
from typing import Callable, Optional

import pytest
from aioredis import Redis
from httpx import AsyncClient

from tests.starlette import run_on_starlette as run_on_framework
from uapi.cookies import CookieSettings
from uapi.login import AsyncLoginSession, configure_async_login
from uapi.sessions.redis import configure_async_sessions
from uapi.starlette import App as FrameworkApp
from uapi.status import Created, NoContent


def configure_login_app(app: FrameworkApp):
    rss = configure_async_sessions(
        app,
        Redis.from_url("redis://", encoding="utf8"),
        cookie_settings=CookieSettings(secure=False),
        max_age=timedelta(seconds=1),
    )
    login_manager = configure_async_login(app, int, rss)

    @app.get("/")
    async def index(current_user_id: Optional[int]) -> str:
        if current_user_id is None:
            return "no user"
        else:
            return str(current_user_id)

    @app.post("/login")
    async def login(login_session: AsyncLoginSession[int]) -> Created[None]:
        return Created(None, await login_session.login_and_return(10))

    @app.post("/logout")
    async def logout(login_session: AsyncLoginSession[int]) -> NoContent[None]:
        return NoContent(None, await login_session.logout_and_return())

    @app.delete("/sessions/{user_id}")
    async def logout_other(current_user_id: int, user_id: int) -> str:
        """The current user is an admin, and is logging out another user."""
        await login_manager.logout(user_id)
        return "OK"


@pytest.fixture(scope="session")
async def login_app(unused_tcp_port_factory: Callable[..., int]):
    unused_tcp_port = unused_tcp_port_factory()
    app = FrameworkApp()
    configure_login_app(app)
    shutdown_event = Event()
    t = create_task(run_on_framework(app, unused_tcp_port, shutdown_event))
    yield unused_tcp_port

    shutdown_event.set()
    await t


async def test_login_logout(login_app: int):
    """Test a normal login/logout workflow."""
    user_id = 10
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == "no user"

        resp = await client.post(
            f"http://localhost:{login_app}/login", params={"user_id": str(user_id)}
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == str(user_id)

        async with AsyncClient() as new_client:
            resp = await new_client.get(f"http://localhost:{login_app}/")
            assert resp.text == "no user"

        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == str(user_id)

        resp = await client.post(f"http://localhost:{login_app}/logout")
        assert resp.text == ""
        assert resp.status_code == 204
        assert not resp.cookies

        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == "no user"


async def test_session_expiry(login_app: int):
    """Test session expiry."""
    user_id = 10
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == "no user"

        resp = await client.post(
            f"http://localhost:{login_app}/login", params={"user_id": user_id}
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == str(user_id)

        await sleep(2)

        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == "no user"


async def test_logging_out_others(login_app: int):
    """Test whether other users can be logged out."""
    user_id = 10
    admin_id = 11
    async with AsyncClient() as client:  # This is the user.
        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == "no user"

        resp = await client.post(
            f"http://localhost:{login_app}/login", params={"user_id": user_id}
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == str(user_id)

        async with AsyncClient() as new_client:  # This is the admin.
            resp = await new_client.delete(f"http://localhost:{login_app}/sessions/10")
            assert resp.status_code == 403

            await new_client.post(
                f"http://localhost:{login_app}/login", params={"user_id": admin_id}
            )
            resp = await new_client.delete(f"http://localhost:{login_app}/sessions/10")
            assert resp.status_code == 200

        resp = await client.get(f"http://localhost:{login_app}/")
        assert resp.text == "no user"
