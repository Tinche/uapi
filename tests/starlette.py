from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.applications import Starlette
from starlette.responses import Response

from attrsapi import Cookie
from attrsapi.starlette import route


def make_app() -> Starlette:
    async def hello() -> str:
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

    async def query_bytes() -> bytes:
        return b"2"

    async def post_no_body() -> Response:
        return Response("post", 201)

    async def post_no_body_no_response() -> None:
        return

    async def post_201() -> tuple[Literal[201], str]:
        return 201, "test"

    async def post_multiple_codes() -> Union[
        tuple[Literal[200], str], tuple[Literal[201], None]
    ]:
        return 201, None

    async def put_cookie(a_cookie: Annotated[str, Cookie()]) -> str:
        return a_cookie

    async def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    app = Starlette(
        routes=[
            route("/", hello),
            route("/path/{path_id}", path),
            route("/query/unannotated", query_unannotated),
            route("/query/string", query_string),
            route("/query", query),
            route("/query-default", query_default),
            route("/query-bytes", query_bytes),
            route("/post/no-body-native-response", post_no_body, methods=["post"]),
            route(
                "/post/no-body-no-response", post_no_body_no_response, methods=["post"]
            ),
            route("/post/201", post_201, methods=["post"]),
            route("/post/multiple", post_multiple_codes, methods=["post"]),
            route("/put/cookie", put_cookie, methods=["put"]),
            route("/put/cookie-optional", put_cookie_optional, methods=["put"]),
        ]
    )
    return app


async def run_server(port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(make_app(), config, shutdown_trigger=shutdown_event.wait)  # type: ignore
