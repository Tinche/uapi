from asyncio import Event, create_task, new_event_loop
from asyncio.exceptions import CancelledError
from typing import AsyncIterator, Callable

import pytest

from .aiohttp import run_server as aiohttp_run_server
from .django import run_server as django_run_server
from .flask import run_server as flask_run_server
from .quart import run_server as quart_run_server
from .starlette import run_server as starlette_run_server


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
        t = create_task(aiohttp_run_server(unused_tcp_port))
        yield unused_tcp_port
        t.cancel()
        try:
            await t
        except CancelledError:
            pass
    elif request.param == "flask":
        shutdown_event = Event()
        t = create_task(flask_run_server(unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "quart":
        shutdown_event = Event()
        t = create_task(quart_run_server(unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "starlette":
        shutdown_event = Event()
        t = create_task(starlette_run_server(unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "django":
        shutdown_event = Event()
        t = create_task(django_run_server(unused_tcp_port, shutdown_event))
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
        t = create_task(aiohttp_run_server(unused_tcp_port, openapi=True))
        yield unused_tcp_port
        t.cancel()
        try:
            await t
        except CancelledError:
            pass
    elif request.param == "flask":
        shutdown_event = Event()
        t = create_task(flask_run_server(unused_tcp_port, shutdown_event, openapi=True))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "quart":
        shutdown_event = Event()
        t = create_task(quart_run_server(unused_tcp_port, shutdown_event, openapi=True))
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "starlette":
        shutdown_event = Event()
        t = create_task(
            starlette_run_server(unused_tcp_port, shutdown_event, openapi=True)
        )
        yield unused_tcp_port
        shutdown_event.set()
        await t
    elif request.param == "django":
        shutdown_event = Event()
        t = create_task(django_run_server(unused_tcp_port, shutdown_event))
        yield unused_tcp_port
        shutdown_event.set()
    else:
        raise Exception("Unknown server framework")
