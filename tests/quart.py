from asyncio import Event

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, Response

from attrsapi.quart import route


async def run_server(port: int, shutdown_event: Event):
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

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(app, config, shutdown_trigger=shutdown_event.wait)
