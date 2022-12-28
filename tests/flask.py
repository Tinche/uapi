from asyncio import Event

from flask import Response, request
from hypercorn.asyncio import serve
from hypercorn.config import Config
from hypercorn.middleware import AsyncioWSGIMiddleware

from uapi import ResponseException
from uapi.flask import App
from uapi.status import NoContent

from .apps import configure_base_sync


def make_app() -> App:
    app = App()

    configure_base_sync(app)

    @app.get("/framework-request")
    def framework_request() -> str:
        return "framework_request" + request.headers["test"]

    @app.post("/framework-resp-subclass")
    def framework_resp_subclass() -> Response:
        return Response("framework_resp_subclass", status=201)

    def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    app.route("/path/<int:path_id>", path)

    @app.options("/unannotated-exception")
    def unannotated_exception() -> Response:
        raise ResponseException(NoContent())

    @app.get("/query/unannotated")
    def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.get("/query/string")
    def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.get("/query")
    def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.get("/query-default")
    def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.post("/post/no-body-native-response")
    def post_no_body() -> Response:
        return Response("post", status=201)

    @app.post("/path1/<path_id>")
    def post_path_string(path_id: str) -> str:
        return str(int(path_id) + 2)

    return app


async def run_server(port: int, shutdown_event: Event, openapi: bool = False):
    config = Config()
    config.bind = [f"localhost:{port}"]

    app = make_app()
    if openapi:
        app.serve_openapi()
    asyncio_app = AsyncioWSGIMiddleware(app.to_framework_app(__name__))
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_flask(app: App, port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(app.to_framework_app(__name__))
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore
