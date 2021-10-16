from aiohttp import web
from aiohttp.web import Response

from attrsapi.aiohttp import SwattrsRouteTableDef


async def run_server(port: int):
    routes = SwattrsRouteTableDef()

    @routes.get("/")
    async def hello() -> Response:
        return Response(text="Hello, world")

    @routes.get("/path/{path_id}")
    async def path_param(path_id: int) -> Response:
        return Response(text=str(path_id + 1))

    @routes.get("/query/unannotated")
    async def query_unannotated(query) -> Response:
        return Response(text=query + "suffix")

    @routes.get("/query/string")
    async def query_string(query: str) -> Response:
        return Response(text=query + "suffix")

    @routes.get("/query")
    async def query_param(page: int) -> Response:
        return Response(text=str(page + 1))

    app = web.Application()
    app.add_routes(routes)
    await web._run_app(app, port=port)
