from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.applications import Starlette
from starlette.responses import Response

from attrsapi import Cookie
from attrsapi.starlette import App


def make_app() -> Starlette:
    app = Starlette()
    attrsapi = App()

    @attrsapi.get("/", starlette=app)
    async def hello() -> str:
        return "Hello, world"

    @attrsapi.route("/path/{path_id}", starlette=app)
    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @attrsapi.route("/query/unannotated", starlette=app)
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @attrsapi.route("/query/string", starlette=app)
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @attrsapi.route("/query", starlette=app)
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @attrsapi.route("/query-default", starlette=app)
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @attrsapi.route("/query-bytes", starlette=app)
    async def query_bytes() -> bytes:
        return b"2"

    @attrsapi.route("/post/no-body-native-response", starlette=app, methods=["POST"])
    async def post_no_body() -> Response:
        return Response("post", 201)

    @attrsapi.route("/post/no-body-no-response", starlette=app, methods=["POST"])
    async def post_no_body_no_response() -> None:
        return

    @attrsapi.route("/post/201", starlette=app, methods=["POST"])
    async def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @attrsapi.route("/post/multiple", starlette=app, methods=["POST"])
    async def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @attrsapi.route("/put/cookie", starlette=app, methods=["PUT"])
    async def put_cookie(a_cookie: Annotated[str, Cookie()]) -> str:
        return a_cookie

    @attrsapi.route("/put/cookie-optional", starlette=app, methods=["PUT"])
    async def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @attrsapi.delete("/delete/header", starlette=app)
    async def delete_with_response_headers() -> tuple[None, Literal[204], dict]:
        return None, 204, {"response": "test"}

    return app


async def run_server(port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(make_app(), config, shutdown_trigger=shutdown_event.wait)  # type: ignore
