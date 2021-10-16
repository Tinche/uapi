from asyncio import Event, create_task
from asyncio.exceptions import CancelledError

import pytest

from .aiohttp import run_server as aiohttp_run_server
from .flask import run_server as flask_run_server
from .quart import run_server as quart_run_server
from .starlette import run_server as starlette_run_server


@pytest.fixture(params=["aiohttp", "flask", "quart", "starlette"])
async def server(request, unused_tcp_port: int):
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
    else:
        raise Exception("Unknown server framework")
