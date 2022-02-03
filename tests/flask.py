from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from flask import Flask, Response
from hypercorn.asyncio import serve
from hypercorn.config import Config
from hypercorn.middleware import AsyncioWSGIMiddleware

from uapi import Cookie
from uapi.cookies import set_cookie
from uapi.flask import App


def make_app():
    flask = Flask("flask")
    app = App()

    @app.get("/", flask=flask)
    def hello() -> str:
        return "Hello, world"

    @app.route("/path/<int:path_id>", flask=flask)
    def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @app.route("/query/unannotated", flask=flask)
    def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.route("/query/string", flask=flask)
    def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.route("/query", flask=flask)
    def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.route("/query-default", flask=flask)
    def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.route("/query-bytes", flask=flask)
    def query_bytes() -> bytes:
        return b"2"

    @app.post("/post/no-body-native-response", flask=flask)
    def post_no_body() -> Response:
        return Response("post", status=201)

    @app.route("/post/no-body-no-response", flask=flask, methods=["post"])
    def post_no_body_no_resp() -> None:
        return

    @app.route("/post/201", flask=flask, methods=["post"])
    def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @app.route("/post/multiple", flask=flask, methods=["post"])
    def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @app.route("/put/cookie", flask=flask, methods=["put"])
    def put_cookie(a_cookie: Annotated[str, Cookie()]) -> str:
        return a_cookie

    @app.route("/put/cookie-optional", flask=flask, methods=["put"])
    def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @app.delete("/delete/header", flask=flask)
    def delete_with_response_headers() -> tuple[None, Literal[204], dict]:
        return None, 204, {"response": "test"}

    @app.patch("/patch/cookie", flask=flask)
    def patch_with_response_cookies() -> tuple[None, Literal[200], dict]:
        return set_cookie((None, 200, {}), "cookie", "my_cookie", 1)

    return flask


async def run_server(port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(make_app())
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_flask(app: App, port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(app.flask)
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore
