from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, Response

from uapi import Cookie
from uapi.cookies import set_cookie
from uapi.quart import App


def make_app() -> Quart:
    quart = Quart("flask")
    app = App()

    @app.get("/", quart=quart)
    async def hello() -> str:
        return "Hello, world"

    @app.route("/path/<int:path_id>", quart=quart)
    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @app.route("/query/unannotated", quart=quart)
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.route("/query/string", quart=quart)
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.route("/query", quart=quart)
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.route("/query-default", quart=quart)
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.route("/query-bytes", quart=quart)
    async def query_bytes() -> bytes:
        return b"2"

    @app.post("/post/no-body-native-response", quart=quart)
    async def post_no_body() -> Response:
        return Response("post", status=201)

    @app.route("/post/no-body-no-response", quart=quart, methods=["post"])
    async def post_no_body_no_resp() -> None:
        return

    @app.route("/post/201", quart=quart, methods=["post"])
    async def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @app.route("/post/multiple", quart=quart, methods=["post"])
    async def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @app.route("/put/cookie", quart=quart, methods=["put"])
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    @app.route("/put/cookie-optional", quart=quart, methods=["put"])
    async def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @app.delete("/delete/header", quart=quart)
    async def delete_with_response_headers() -> tuple[None, Literal[204], dict]:
        return None, 204, {"response": "test"}

    @app.patch("/patch/cookie", quart=quart)
    async def patch_with_response_cookies() -> tuple[None, Literal[200], dict]:
        return set_cookie((None, 200, {}), "cookie", "my_cookie", 1)

    return quart


async def run_server(port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]
    try:
        app = make_app()
    except Exception as exc:
        print(exc)
        raise
    await serve(app, config, shutdown_trigger=shutdown_event.wait)  # type: ignore


async def run_on_quart(app: App, port: int, shutdown_event: Event):
    config = Config()
    config.bind = [f"localhost:{port}"]
    await serve(app.quart, config, shutdown_trigger=shutdown_event.wait)  # type: ignore
