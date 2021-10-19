from asyncio import Event

from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.applications import Starlette
from starlette.responses import Response

from attrsapi.starlette import route


def make_app() -> Starlette:
    async def hello():
        return "Hello, world"

    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    async def query(page: int) -> Response:
        return Response(str(page + 1))

    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    app = Starlette(
        routes=[
            route("/", hello),
            route("/path/{path_id}", path),
            route("/query/unannotated", query_unannotated),
            route("/query/string", query_string),
            route("/query", query),
            route("/query-default", query_default),
        ]
    )
    return app


async def run_server(port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(make_app(), config, shutdown_trigger=shutdown_event.wait)  # type: ignore
