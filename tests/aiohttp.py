from typing import Annotated, Optional, Union

from aiohttp import web
from aiohttp.web import Response

from uapi import Cookie, ResponseException
from uapi.aiohttp import App
from uapi.cookies import CookieSettings, set_cookie
from uapi.status import Created, Forbidden, NoContent, Ok

from .apps import make_generic_subapp
from .models import NestedModel, SimpleModel


def make_app() -> App:
    app = App()

    @app.get("/")
    @app.post("/")
    async def hello() -> str:
        return "Hello, world"

    async def path_param(path_id: int) -> Response:
        return Response(text=str(path_id + 1))

    app.route("/path/{path_id}", path_param)

    @app.get("/query/unannotated")
    async def query_unannotated(query) -> Response:
        return Response(text=query + "suffix")

    @app.get("/query/string")
    async def query_string(query: str) -> Response:
        return Response(text=query + "suffix")

    @app.get("/query")
    async def query_param(page: int) -> Response:
        return Response(text=str(page + 1))

    @app.get("/query-default")
    async def query_default(page: int = 0) -> Response:
        return Response(text=str(page + 1))

    @app.get("/query-bytes")
    async def query_bytes() -> bytes:
        return b"2"

    @app.get("/get/model")
    async def get_model() -> NestedModel:
        return NestedModel()

    @app.get("/get/model-status")
    async def get_model_status() -> Created[NestedModel]:
        return Created(NestedModel(), {"test": "test"})

    @app.post("/post/no-body-native-response")
    async def post_no_body() -> Response:
        return Response(text="post", status=201)

    async def post_no_body_no_resp() -> None:
        return

    app.route("/post/no-body-no-response", post_no_body_no_resp, methods=["POST"])

    @app.post("/post/201")
    async def post_201() -> Created[str]:
        return Created("test")

    @app.post("/post/multiple")
    async def post_multiple_codes() -> Union[Ok[str], Created[None]]:
        return Created(None)

    @app.post("/post/model")
    async def post_model(body: NestedModel) -> Created[NestedModel]:
        return Created(body)

    @app.put("/put/cookie")
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    async def put_cookie_opt(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    app.route("/put/cookie-optional", put_cookie_opt, methods=["PUT"])

    @app.delete("/delete/header")
    async def delete_with_response_headers() -> NoContent[None]:
        return NoContent(None, {"response": "test"})

    @app.patch("/patch/cookie")
    async def patch_with_response_cookies() -> Ok[None]:
        return Ok(None, set_cookie("cookie", "my_cookie", CookieSettings(max_age=1)))

    async def patch_attrs_union() -> NestedModel | Created[SimpleModel]:
        return NestedModel()

    app.route("/patch/attrs", patch_attrs_union, methods=["patch"])

    @app.head("/head/exc")
    async def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

    app.route_app(make_generic_subapp())
    app.route_app(make_generic_subapp(), "/subapp", "subapp")

    return app


async def run_server(port: int, openapi: bool = False):
    try:
        app = make_app()
        if openapi:
            app.serve_openapi()
        aapp = web.Application()
        aapp.add_routes(app.to_framework_routes())
        await web._run_app(aapp, port=port, handle_signals=False)
    except Exception as exc:
        print(exc)
        raise


async def run_on_aiohttp(app: App, port: int):
    try:
        aiohttp_app = web.Application()
        aiohttp_app.add_routes(app.to_framework_routes())
        await web._run_app(aiohttp_app, port=port, handle_signals=False)
    except Exception as exc:
        print(exc)
        raise
