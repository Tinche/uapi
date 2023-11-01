from asyncio import Event

from hypercorn.asyncio import serve
from hypercorn.config import Config


async def run_on_django(port: int, shutdown_event: Event):
    from .django_uapi.django_uapi.wsgi import application

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(application, config, shutdown_trigger=shutdown_event.wait, mode="wsgi")  # type: ignore
