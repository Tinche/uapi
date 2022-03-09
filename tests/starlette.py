from asyncio import Event
from typing import Annotated, Optional, Union

from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.applications import Starlette
from starlette.responses import Response

from uapi import Cookie, ResponseException
from uapi.cookies import CookieSettings, set_cookie
from uapi.starlette import App
from uapi.status import Created, Forbidden, NoContent, Ok

from .models import NestedModel


def make_app() -> Starlette:
    starlette = Starlette()
    app = App()

    @app.get("/", starlette=starlette)
    async def hello() -> str:
        return "Hello, world"

    @app.route("/path/{path_id}", starlette=starlette)
    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @app.route("/query/unannotated", starlette=starlette)
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.route("/query/string", starlette=starlette)
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.route("/query", starlette=starlette)
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.route("/query-default", starlette=starlette)
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.route("/query-bytes", starlette=starlette)
    async def query_bytes() -> bytes:
        return b"2"

    @app.get("/get/model", starlette=starlette)
    async def get_model() -> NestedModel:
        return NestedModel()

    @app.get("/get/model-status", starlette=starlette)
    async def get_model_status() -> Created[NestedModel]:
        return Created(NestedModel(), {"test": "test"})

    @app.post("/post/no-body-native-response", starlette=starlette)
    async def post_no_body() -> Response:
        return Response("post", 201)

    @app.route("/post/no-body-no-response", starlette=starlette, methods=["POST"])
    async def post_no_body_no_response() -> None:
        return

    @app.route("/post/201", starlette=starlette, methods=["POST"])
    async def post_201() -> Created[str]:
        return Created("test")

    @app.route("/post/multiple", starlette=starlette, methods=["POST"])
    async def post_multiple_codes() -> Union[Ok[str], Created[None]]:
        return Created(None)

    @app.post("/post/model", starlette=starlette)
    async def post_model(body: NestedModel) -> Created[NestedModel]:
        return Created(body)

    @app.put("/put/cookie", starlette=starlette)
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    @app.route("/put/cookie-optional", starlette=starlette, methods=["PUT"])
    async def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @app.delete("/delete/header", starlette=starlette)
    async def delete_with_response_headers() -> NoContent[None]:
        return NoContent(None, {"response": "test"})

    @app.patch("/patch/cookie", starlette=starlette)
    async def patch_with_response_cookies() -> Ok[None]:
        return Ok(None, set_cookie("cookie", "my_cookie", CookieSettings(max_age=1)))

    @app.head("/head/exc", starlette=starlette)
    async def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

    return starlette


async def run_server(port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(make_app(), config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_starlette(app: App, port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(app.starlette, config, shutdown_trigger=shutdown_event.wait)  # type: ignore
