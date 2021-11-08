from typing import Annotated, Literal, Optional, Union

from aiohttp import web
from aiohttp.web import Response, RouteTableDef

from attrsapi import Cookie
from attrsapi.aiohttp import route


def make_app() -> web.Application:
    routes = RouteTableDef()

    @route(routes, "get", "/")
    async def hello() -> str:
        return "Hello, world"

    @route(routes, "get", "/path/{path_id}")
    async def path_param(path_id: int) -> Response:
        return Response(text=str(path_id + 1))

    @route(routes, "get", "/query/unannotated")
    async def query_unannotated(query) -> Response:
        return Response(text=query + "suffix")

    @route(routes, "get", "/query/string")
    async def query_string(query: str) -> Response:
        return Response(text=query + "suffix")

    @route(routes, "get", "/query")
    async def query_param(page: int) -> Response:
        return Response(text=str(page + 1))

    @route(routes, "get", "/query-default")
    async def query_default(page: int = 0) -> Response:
        return Response(text=str(page + 1))

    @route(routes, "get", "/query-bytes")
    async def query_bytes() -> bytes:
        return b"2"

    @route(routes, "post", "/post/no-body-native-response")
    async def post_no_body() -> Response:
        return Response(text="post", status=201)

    @route(routes, "post", "/post/no-body-no-response")
    async def post_no_body_no_resp() -> None:
        return

    @route(routes, "post", "/post/201")
    async def post_201() -> tuple[Literal[201], str]:
        return 201, "test"

    @route(routes, "post", "/post/multiple")
    async def post_multiple_codes() -> Union[
        tuple[Literal[200], str], tuple[Literal[201], None]
    ]:
        return 201, None

    @route(routes, "put", "/put/cookie")
    async def put_cookie(a_cookie: Annotated[str, Cookie()]) -> str:
        return a_cookie

    @route(routes, "put", "/put/cookie-optional")
    async def put_cookie_opt(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    app = web.Application()
    app.add_routes(routes)
    return app


async def run_server(port: int):
    app = make_app()
    await web._run_app(app, port=port)
