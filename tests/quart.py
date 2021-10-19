from asyncio import Event

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, Response

from attrsapi.quart import route


def make_app() -> Quart:
    app = Quart("flask")

    @app.get("/")
    async def hello():
        return "Hello, world"

    @route("/path/<path_id>", app)
    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @route("/query/unannotated", app)
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @route("/query/string", app)
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @route("/query", app)
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @route("/query-default", app)
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    return app


async def run_server(port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(make_app(), config, shutdown_trigger=shutdown_event.wait)
