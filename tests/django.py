from asyncio import CancelledError, Event, create_task

from hypercorn.asyncio import serve
from hypercorn.config import Config

from uapi.django import DjangoApp

# Sigh
urlpatterns: list = []


async def run_on_django(app: DjangoApp, port: int) -> None:
    from django.conf import settings
    from django.core.handlers.wsgi import WSGIHandler

    urlpatterns.clear()
    urlpatterns.extend(app.to_urlpatterns())

    if not settings.configured:
        settings.configure(ROOT_URLCONF=__name__, DEBUG=True)

    application = WSGIHandler()

    config = Config()
    config.bind = [f"localhost:{port}"]

    event = Event()

    t = create_task(
        serve(application, config, shutdown_trigger=event.wait, mode="wsgi")  # type: ignore
    )

    try:
        await t
    except CancelledError:
        event.set()
        await t
        raise
    finally:
        urlpatterns.clear()
