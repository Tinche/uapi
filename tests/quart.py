from asyncio import Event

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Response, request

from uapi import ResponseException
from uapi.quart import App
from uapi.status import NoContent

from .apps import configure_base_async


def make_app() -> App:
    app = App()

    configure_base_async(app)

    @app.get("/framework-request")
    async def framework_request() -> str:
        return "framework_request" + request.headers["test"]

    @app.post("/framework-resp-subclass")
    async def framework_resp_subclass() -> Response:
        return Response("framework_resp_subclass", status=201)

    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    app.route("/path/<int:path_id>", path)

    @app.post("/path1/<path_id>")
    async def post_path_string(path_id: str) -> str:
        return str(int(path_id) + 2)

    @app.options("/unannotated-exception")
    async def unannotated_exception() -> Response:
        raise ResponseException(NoContent())

    @app.get("/query/unannotated", tags=["query"])
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.get("/query/string", tags=["query"])
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.get("/query", tags=["query"])
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.get("/query-default", tags=["query"])
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.post("/post/no-body-native-response")
    async def post_no_body() -> Response:
        return Response("post", status=201)

    return app


async def run_server(port: int, shutdown_event: Event, openapi: bool = False):
    config = Config()
    config.bind = [f"localhost:{port}"]
    try:
        app = make_app()
    except Exception as exc:
        print(exc)
        raise
    if openapi:
        app.serve_openapi()
    await serve(app.to_framework_app(__name__), config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_quart(app: App, port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]
    await serve(app.to_framework_app(__name__), config, shutdown_trigger=shutdown_event.wait)  # type: ignore
