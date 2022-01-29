from typing import Annotated, Literal, Optional, Union

from aiohttp import web
from aiohttp.web import Response, RouteTableDef

from attrsapi import Cookie
from attrsapi.aiohttp import App


def make_app() -> web.Application:
    routes = RouteTableDef()
    attrsapi = App()

    @attrsapi.route("/", routes)
    async def hello() -> str:
        return "Hello, world"

    @attrsapi.route("/path/{path_id}", routes)
    async def path_param(path_id: int) -> Response:
        return Response(text=str(path_id + 1))

    @attrsapi.route("/query/unannotated", routes)
    async def query_unannotated(query) -> Response:
        print(query)
        return Response(text=query + "suffix")

    @attrsapi.route("/query/string", routes)
    async def query_string(query: str) -> Response:
        return Response(text=query + "suffix")

    @attrsapi.route("/query", routes)
    async def query_param(page: int) -> Response:
        return Response(text=str(page + 1))

    @attrsapi.route("/query-default", routes)
    async def query_default(page: int = 0) -> Response:
        return Response(text=str(page + 1))

    @attrsapi.route("/query-bytes", routes)
    async def query_bytes() -> bytes:
        return b"2"

    @attrsapi.route("/post/no-body-native-response", routes, methods=["POST"])
    async def post_no_body() -> Response:
        return Response(text="post", status=201)

    @attrsapi.route("/post/no-body-no-response", routes, methods=["POST"])
    async def post_no_body_no_resp() -> None:
        return

    @attrsapi.route("/post/201", routes, methods=["POST"])
    async def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @attrsapi.route("/post/multiple", routes, methods=["POST"])
    async def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @attrsapi.route("/put/cookie", routes, methods=["PUT"])
    async def put_cookie(a_cookie: Annotated[str, Cookie()]) -> str:
        return a_cookie

    @attrsapi.route("/put/cookie-optional", routes, methods=["PUT"])
    async def put_cookie_opt(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    app = web.Application()
    app.add_routes(routes)
    return app


async def run_server(port: int):
    try:
        app = make_app()
    except Exception as exc:
        print(exc)
    await web._run_app(app, port=port, handle_signals=False)
