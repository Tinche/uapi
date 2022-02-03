from typing import Annotated, Literal, Optional, Union

from aiohttp import web
from aiohttp.web import Response, RouteTableDef

from uapi import Cookie
from uapi.aiohttp import App
from uapi.cookies import set_cookie


def make_app() -> web.Application:
    routes = RouteTableDef()
    app = App()

    @app.get("/", routes=routes)
    async def hello() -> str:
        return "Hello, world"

    @app.route("/path/{path_id}", routes=routes)
    async def path_param(path_id: int) -> Response:
        return Response(text=str(path_id + 1))

    @app.route("/query/unannotated", routes=routes)
    async def query_unannotated(query) -> Response:
        return Response(text=query + "suffix")

    @app.route("/query/string", routes=routes)
    async def query_string(query: str) -> Response:
        return Response(text=query + "suffix")

    @app.route("/query", routes=routes)
    async def query_param(page: int) -> Response:
        return Response(text=str(page + 1))

    @app.route("/query-default", routes=routes)
    async def query_default(page: int = 0) -> Response:
        return Response(text=str(page + 1))

    @app.route("/query-bytes", routes=routes)
    async def query_bytes() -> bytes:
        return b"2"

    @app.post("/post/no-body-native-response", routes=routes)
    async def post_no_body() -> Response:
        return Response(text="post", status=201)

    @app.route("/post/no-body-no-response", routes=routes, methods=["POST"])
    async def post_no_body_no_resp() -> None:
        return

    @app.route("/post/201", routes=routes, methods=["POST"])
    async def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @app.route("/post/multiple", routes=routes, methods=["POST"])
    async def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @app.route("/put/cookie", routes=routes, methods=["PUT"])
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    @app.route("/put/cookie-optional", routes=routes, methods=["PUT"])
    async def put_cookie_opt(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @app.delete("/delete/header", routes=routes)
    async def delete_with_response_headers() -> tuple[None, Literal[204], dict]:
        return None, 204, {"response": "test"}

    @app.patch("/patch/cookie", routes=routes)
    async def patch_with_response_cookies() -> tuple[None, Literal[200], dict]:
        return set_cookie((None, 200, {}), "cookie", "my_cookie", 1)

    aapp = web.Application()
    aapp.add_routes(routes)
    return aapp


async def run_server(port: int):
    try:
        app = make_app()
        await web._run_app(app, port=port, handle_signals=False)
    except Exception as exc:
        print(exc)
        raise


async def run_on_aiohttp(app: App, port: int):
    try:
        aiohttp_app = web.Application()
        aiohttp_app.add_routes(app.routes)
        await web._run_app(aiohttp_app, port=port, handle_signals=False)
    except Exception as exc:
        print(exc)
        raise
