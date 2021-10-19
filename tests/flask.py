from asyncio import Event

from flask import Flask, Response
from hypercorn.asyncio import serve
from hypercorn.config import Config
from hypercorn.middleware import AsyncioWSGIMiddleware

from attrsapi.flask import route


def make_app():
    app = Flask("flask")

    @app.get("/")
    def hello():
        return "Hello, world"

    @route("/path/<path_id>", app)
    def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @route("/query/unannotated", app)
    def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @route("/query/string", app)
    def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @route("/query", app)
    def query(page: int) -> Response:
        return Response(str(page + 1))

    @route("/query-default", app)
    def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    return app


async def run_server(port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(make_app())
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)
