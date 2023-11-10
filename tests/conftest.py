from asyncio import Event, create_task, new_event_loop
from asyncio.exceptions import CancelledError
from collections.abc import AsyncIterator, Callable
from contextlib import suppress

import pytest

from .aiohttp import make_app as make_aiohttp_app
from .aiohttp import run_on_aiohttp
from .django import run_on_django
from .flask import make_app as make_flask_app
from .flask import run_on_flask
from .quart import make_app as make_quart_app
from .quart import run_on_quart
from .starlette import make_app as make_starlette_app
from .starlette import run_on_starlette


@pytest.fixture(scope="session")
def event_loop():
    loop = new_event_loop()
    try:
        yield loop
    finally:
        loop.close()


@pytest.fixture(
    params=["aiohttp", "flask", "quart", "starlette", "django"], scope="session"
)
async def server(request, unused_tcp_port_factory: Callable[..., int]):
    unused_tcp_port = unused_tcp_port_factory()
    if request.param == "aiohttp":
        t = create_task(run_on_aiohttp(make_aiohttp_app(), unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        with suppress(CancelledError):
            await t
    elif request.param == "flask":
        shutdown_event = Event()
        t = create_task(run_on_flask(make_flask_app(), unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "quart":
        shutdown_event = Event()
        t = create_task(run_on_quart(make_quart_app(), unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        with suppress(CancelledError):
            await t
    elif request.param == "starlette":
        t = create_task(run_on_starlette(make_starlette_app(), unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        with suppress(CancelledError):
            await t
    elif request.param == "django":
        shutdown_event = Event()
        t = create_task(run_on_django(unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    else:
        raise Exception("Unknown server framework")


@pytest.fixture(
    params=["aiohttp", "flask", "quart", "starlette", "django"], scope="session"
)
async def server_with_openapi(
    request, unused_tcp_port_factory: Callable[[], int]
) -> AsyncIterator[int]:
    unused_tcp_port = unused_tcp_port_factory()
    if request.param == "aiohttp":
        aiohttp_app = make_aiohttp_app()
        aiohttp_app.serve_openapi()
        t = create_task(run_on_aiohttp(aiohttp_app, unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        with suppress(CancelledError):
            await t
    elif request.param == "flask":
        shutdown_event = Event()
        flask_app = make_flask_app()
        flask_app.serve_openapi()
        t = create_task(run_on_flask(flask_app, unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "quart":
        quart_app = make_quart_app()
        quart_app.serve_openapi()
        t = create_task(run_on_quart(quart_app, unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        with suppress(CancelledError):
            await t
    elif request.param == "starlette":
        starlette_app = make_starlette_app()
        starlette_app.serve_openapi()
        t = create_task(run_on_starlette(starlette_app, unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        with suppress(CancelledError):
            await t
    elif request.param == "django":
        shutdown_event = Event()
        t = create_task(run_on_django(unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    else:
        raise Exception("Unknown server framework")
