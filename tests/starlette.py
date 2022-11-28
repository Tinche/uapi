from asyncio import Event

from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.responses import Response

from uapi import ResponseException
from uapi.starlette import App
from uapi.status import NoContent

from .apps import configure_base_async


def make_app() -> App:
    app = App()
    configure_base_async(app)

    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    app.route("/path/{path_id}", path)

    @app.options("/unannotated-exception")
    async def unannotated_exception() -> Response:
        raise ResponseException(NoContent())

    @app.post("/post/no-body-native-response")
    async def post_no_body() -> Response:
        return Response("post", 201)

    @app.get("/query/unannotated")
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.get("/query/string")
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.get("/query")
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.get("/query-default")
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.post("/path1/{path_id}")
    async def post_path_string(path_id: str) -> str:
        return str(int(path_id) + 2)

    return app


async def run_server(port: int, shutdown_event: Event, openapi: bool = False):

    config = Config()
    config.bind = [f"localhost:{port}"]

    app = make_app()
    if openapi:
        app.serve_openapi()

    await serve(app.to_framework_app(), config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_starlette(app: App, port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(app.to_framework_app(), config, shutdown_trigger=shutdown_event.wait)  # type: ignore
