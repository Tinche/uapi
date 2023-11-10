from asyncio import Event

from flask import Response, request
from hypercorn.asyncio import serve
from hypercorn.config import Config

from uapi import ResponseException
from uapi.flask import App
from uapi.status import NoContent
from uapi.types import Method, RouteName

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

    @app.get("/query/unannotated", tags=["query"])
    def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.get("/query/string", tags=["query"])
    def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.get("/query", tags=["query"])
    def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.get("/query-default", tags=["query"])
    def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.post("/post/no-body-native-response")
    def post_no_body() -> Response:
        return Response("post", status=201)

    @app.post("/path1/<path_id>")
    def post_path_string(path_id: str) -> str:
        return str(int(path_id) + 2)

    # Route name composition.
    @app.get("/comp/route-name-native")
    @app.post("/comp/route-name-native", name="route-name-native-post")
    def route_name_native(route_name: RouteName) -> Response:
        return Response(route_name)

    # Request method composition.
    @app.get("/comp/req-method-native")
    @app.post("/comp/req-method-native", name="request-method-native-post")
    def request_method_native(req_method: Method) -> Response:
        return Response(req_method)

    return app


async def run_on_flask(app: App, port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(
        app.to_framework_app(__name__),
        config,
        shutdown_trigger=shutdown_event.wait,  # type: ignore
        mode="wsgi",
    )
