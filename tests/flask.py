from asyncio import Event
from typing import Annotated, Optional, Union

from flask import Flask, Response
from hypercorn.asyncio import serve
from hypercorn.config import Config
from hypercorn.middleware import AsyncioWSGIMiddleware

from uapi import Cookie, ResponseException
from uapi.cookies import CookieSettings, set_cookie
from uapi.flask import App
from uapi.status import Created, Forbidden, NoContent, Ok

from .models import NestedModel, SimpleModel


def make_app() -> App:
    app = App()

    @app.get("/")
    @app.post("/", name="hello-post")
    def hello() -> str:
        return "Hello, world"

    def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    app.route("/path/<int:path_id>", path)

    @app.get("/query/unannotated")
    def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.get("/query/string")
    def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.get("/query")
    def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.get("/query-default")
    def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.get("/query-bytes")
    def query_bytes() -> bytes:
        return b"2"

    @app.get("/get/model")
    def get_model() -> NestedModel:
        return NestedModel()

    @app.get("/get/model-status")
    def get_model_status() -> Created[NestedModel]:
        return Created(NestedModel(), {"test": "test"})

    @app.post("/post/no-body-native-response")
    def post_no_body() -> Response:
        return Response("post", status=201)

    def post_no_body_no_resp() -> None:
        return

    app.route("/post/no-body-no-response", post_no_body_no_resp, methods=["post"])

    @app.post("/post/201")
    def post_201() -> Created[str]:
        return Created("test")

    @app.post("/post/multiple")
    def post_multiple_codes() -> Union[Ok[str], Created[None]]:
        return Created(None)

    @app.post("/post/model")
    def post_model(body: NestedModel) -> Created[NestedModel]:
        return Created(body)

    @app.put("/put/cookie")
    def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    app.route("/put/cookie-optional", put_cookie_optional, methods=["put"])

    @app.delete("/delete/header")
    def delete_with_response_headers() -> NoContent[None]:
        return NoContent(None, {"response": "test"})

    @app.patch("/patch/cookie")
    def patch_with_response_cookies() -> Ok[None]:
        return Ok(None, set_cookie("cookie", "my_cookie", CookieSettings(max_age=1)))

    def patch_attrs_union() -> NestedModel | Created[SimpleModel]:
        return NestedModel()

    app.route("/patch/attrs", patch_attrs_union, methods=["patch"])

    @app.head("/head/exc")
    def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

    return app


async def run_server(port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(make_app().to_framework_app(__name__))
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_flask(app: App, port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]

    asyncio_app = AsyncioWSGIMiddleware(app.to_framework_app(__name__))
    await serve(asyncio_app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore
