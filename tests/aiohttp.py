from typing import Annotated, Optional, Union

from aiohttp import web
from aiohttp.web import Response, RouteTableDef

from uapi import Cookie, ResponseException
from uapi.aiohttp import App
from uapi.cookies import CookieSettings, set_cookie
from uapi.status import Created, Forbidden, NoContent, Ok

from .models import NestedModel


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

    @app.get("/get/model", routes=routes)
    async def get_model() -> NestedModel:
        return NestedModel()

    @app.get("/get/model-status", routes=routes)
    async def get_model_status() -> Created[NestedModel]:
        return Created(NestedModel(), {"test": "test"})

    @app.post("/post/no-body-native-response", routes=routes)
    async def post_no_body() -> Response:
        return Response(text="post", status=201)

    @app.route("/post/no-body-no-response", routes=routes, methods=["POST"])
    async def post_no_body_no_resp() -> None:
        return

    @app.route("/post/201", routes=routes, methods=["POST"])
    async def post_201() -> Created[str]:
        return Created("test")

    @app.route("/post/multiple", routes=routes, methods=["POST"])
    async def post_multiple_codes() -> Union[Ok[str], Created[None]]:
        return Created(None)

    @app.post("/post/model", routes=routes)
    async def post_model(body: NestedModel) -> Created[NestedModel]:
        return Created(body)

    @app.put("/put/cookie", routes=routes)
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    @app.route("/put/cookie-optional", routes=routes, methods=["PUT"])
    async def put_cookie_opt(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @app.delete("/delete/header", routes=routes)
    async def delete_with_response_headers() -> NoContent[None]:
        return NoContent(None, {"response": "test"})

    @app.patch("/patch/cookie", routes=routes)
    async def patch_with_response_cookies() -> Ok[None]:
        return Ok(None, set_cookie("cookie", "my_cookie", CookieSettings(max_age=1)))

    @app.head("/head/exc", routes=routes)
    async def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

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
