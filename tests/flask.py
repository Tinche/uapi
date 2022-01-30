from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from flask import Flask, Response
from hypercorn.asyncio import serve
from hypercorn.config import Config
from hypercorn.middleware import AsyncioWSGIMiddleware

from attrsapi import Cookie
from attrsapi.flask import App


def make_app():
    app = Flask("flask")
    attrsapi = App()

    @attrsapi.get("/", flask=app)
    def hello() -> str:
        return "Hello, world"

    @attrsapi.route("/path/<int:path_id>", flask=app)
    def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @attrsapi.route("/query/unannotated", flask=app)
    def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @attrsapi.route("/query/string", flask=app)
    def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @attrsapi.route("/query", flask=app)
    def query(page: int) -> Response:
        return Response(str(page + 1))

    @attrsapi.route("/query-default", flask=app)
    def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @attrsapi.route("/query-bytes", flask=app)
    def query_bytes() -> bytes:
        return b"2"

    @attrsapi.route("/post/no-body-native-response", flask=app, methods=["post"])
    def post_no_body() -> Response:
        return Response("post", status=201)

    @attrsapi.route("/post/no-body-no-response", flask=app, methods=["post"])
    def post_no_body_no_resp() -> None:
        return

    @attrsapi.route("/post/201", flask=app, methods=["post"])
    def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @attrsapi.route("/post/multiple", flask=app, methods=["post"])
    def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @attrsapi.route("/put/cookie", flask=app, methods=["put"])
    def put_cookie(a_cookie: Annotated[str, Cookie()]) -> str:
        return a_cookie

    @attrsapi.route("/put/cookie-optional", flask=app, methods=["put"])
    def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @attrsapi.delete("/delete/header", flask=app)
    def delete_with_response_headers() -> tuple[None, Literal[204], dict]:
        return None, 204, {"response": "test"}

    return app


async def run_server(port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(make_app())
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)
