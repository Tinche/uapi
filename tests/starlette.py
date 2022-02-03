from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from hypercorn.asyncio import serve
from hypercorn.config import Config
from starlette.applications import Starlette
from starlette.responses import Response

from uapi import Cookie
from uapi.cookies import set_cookie
from uapi.starlette import App


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

    @app.post("/post/no-body-native-response", starlette=starlette)
    async def post_no_body() -> Response:
        return Response("post", 201)

    @app.route("/post/no-body-no-response", starlette=starlette, methods=["POST"])
    async def post_no_body_no_response() -> None:
        return

    @app.route("/post/201", starlette=starlette, methods=["POST"])
    async def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @app.route("/post/multiple", starlette=starlette, methods=["POST"])
    async def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @app.route("/put/cookie", starlette=starlette, methods=["PUT"])
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    @app.route("/put/cookie-optional", starlette=starlette, methods=["PUT"])
    async def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @app.delete("/delete/header", starlette=starlette)
    async def delete_with_response_headers() -> tuple[None, Literal[204], dict]:
        return None, 204, {"response": "test"}

    @app.patch("/patch/cookie", starlette=starlette)
    async def patch_with_response_cookies() -> tuple[None, Literal[200], dict]:
        return set_cookie((None, 200, {}), "cookie", "my_cookie", 1)

    return starlette


async def run_server(port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(make_app(), config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_starlette(app: App, port: int, shutdown_event: Event):

    config = Config()
    config.bind = [f"localhost:{port}"]

    await serve(app.starlette, config, shutdown_trigger=shutdown_event.wait)  # type: ignore
