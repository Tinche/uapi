from typing import Literal

from aiohttp import web
from aiohttp.web import Response, RouteTableDef

from attrsapi.aiohttp import route


def make_app() -> web.Application:
    routes = RouteTableDef()

    @route(routes, "get", "/")
    async def hello() -> Response:
        return Response(text="Hello, world")

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

    @route(routes, "post", "/post/no-body-native-response")
    async def post_no_body() -> Response:
        return Response(text="post", status=201)

    @route(routes, "post", "/post/no-body-no-response")
    async def post_no_body_no_resp() -> None:
        return

    @route(routes, "post", "/post/201")
    async def post_201() -> tuple[Literal[201], str]:
        return 201, "test"

    app = web.Application()
    app.add_routes(routes)
    return app


async def run_server(port: int):
    app = make_app()
    await web._run_app(app, port=port)
