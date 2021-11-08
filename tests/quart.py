from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, Response

from attrsapi import Cookie
from attrsapi.quart import route


def make_app() -> Quart:
    app = Quart("flask")

    @route("/", app)
    async def hello() -> str:
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

    @route("/query-bytes", app)
    async def query_bytes() -> bytes:
        return b"2"

    @route("/post/no-body-native-response", app, methods=["post"])
    async def post_no_body() -> Response:
        return Response("post", status=201)

    @route("/post/no-body-no-response", app, methods=["post"])
    async def post_no_body_no_resp() -> None:
        return

    @route("/post/201", app, methods=["post"])
    async def post_201() -> tuple[Literal[201], str]:
        return 201, "test"

    @route("/post/multiple", app, methods=["post"])
    async def post_multiple_codes() -> Union[
        tuple[Literal[200], str], tuple[Literal[201], None]
    ]:
        return 201, None

    @route("/put/cookie", app, methods=["put"])
    async def put_cookie(a_cookie: Annotated[str, Cookie()]) -> str:
        return a_cookie

    @route("/put/cookie-optional", app, methods=["put"])
    async def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    return app


async def run_server(port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(make_app(), config, shutdown_trigger=shutdown_event.wait)
