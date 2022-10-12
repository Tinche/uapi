from asyncio import Event

from hypercorn.asyncio import serve
from hypercorn.config import Config
from hypercorn.middleware import AsyncioWSGIMiddleware


async def run_server(port: int, shutdown_event: Event):
    from .django_uapi.django_uapi.wsgi import application

    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(application)
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore
