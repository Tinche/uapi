from asyncio import CancelledError, Event, create_task
from typing import Callable, Literal, Union

import pytest

from uapi.aiohttp import App as AiohttpApp
from uapi.cookies import CookieSettings
from uapi.flask import App as FlaskApp
from uapi.quart import App as QuartApp
from uapi.sessions import Session, configure_secure_sessions
from uapi.starlette import App as StarletteApp
from uapi.status import Created, NoContent

from ..aiohttp import run_on_aiohttp
from ..flask import run_on_flask
from ..quart import run_on_quart
from ..starlette import run_on_starlette


def configure_secure_session_app(
    app: Union[AiohttpApp, QuartApp, StarletteApp, FlaskApp]
):
    configure_secure_sessions(
        app, "test", settings=CookieSettings(max_age=1, secure=False)
    )

    if isinstance(app, FlaskApp):

        @app.get("/")
        def index(session: Session) -> str:
            if "user_id" not in session:
                return "naughty!"
            else:
                return session["user_id"]

        @app.post("/login")
        def login(username: str, session: Session) -> Created[None]:
            session["user_id"] = username
            return Created(None, session.update_session())

        @app.post("/logout")
        def logout(session: Session) -> NoContent[None]:
            session.pop("user_id", None)
            return NoContent(None, session.update_session())

    else:

        @app.get("/")
        async def index(session: Session) -> str:
            if "user_id" not in session:
                return "naughty!"
            else:
                return session["user_id"]

        @app.post("/login")
        async def login(username: str, session: Session) -> Created[None]:
            session["user_id"] = username
            return Created(None, session.update_session())

        @app.post("/logout")
        async def logout(session: Session) -> NoContent[None]:
            session.pop("user_id", None)
            return NoContent(None, session.update_session())


@pytest.fixture(params=["aiohttp", "flask", "quart", "starlette"], scope="session")
async def secure_cookie_session_app(
    request, unused_tcp_port_factory: Callable[..., int]
):
    unused_tcp_port = unused_tcp_port_factory()
    if request.param == "aiohttp":
        app = AiohttpApp()
        configure_secure_session_app(app)
        t = create_task(run_on_aiohttp(app, unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        try:
            await t
        except CancelledError:
            pass
    elif request.param == "flask":
        flask_app = FlaskApp()
        configure_secure_session_app(flask_app)
        shutdown_event = Event()
        t = create_task(run_on_flask(flask_app, unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "quart":
        quart_app = QuartApp()
        configure_secure_session_app(quart_app)
        shutdown_event = Event()
        t = create_task(run_on_quart(quart_app, unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "starlette":
        starlette_app = StarletteApp()
        configure_secure_session_app(starlette_app)
        shutdown_event = Event()
        t = create_task(
            run_on_starlette(starlette_app, unused_tcp_port, shutdown_event)
        )
        yield unused_tcp_port
        shutdown_event.set()
        await t
    else:
        raise Exception("Unknown server framework")
