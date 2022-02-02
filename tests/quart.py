from asyncio import Event
from typing import Annotated, Literal, Optional, Union

from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, Response

from attrsapi import Cookie
from attrsapi.cookies import set_cookie
from attrsapi.quart import App


def make_app() -> Quart:
    app = Quart("flask")
    attrsapi = App()

    @attrsapi.get("/", quart=app)
    async def hello() -> str:
        return "Hello, world"

    @attrsapi.route("/path/<int:path_id>", quart=app)
    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    @attrsapi.route("/query/unannotated", quart=app)
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @attrsapi.route("/query/string", quart=app)
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @attrsapi.route("/query", quart=app)
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @attrsapi.route("/query-default", quart=app)
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @attrsapi.route("/query-bytes", quart=app)
    async def query_bytes() -> bytes:
        return b"2"

    @attrsapi.post("/post/no-body-native-response", quart=app)
    async def post_no_body() -> Response:
        return Response("post", status=201)

    @attrsapi.route("/post/no-body-no-response", quart=app, methods=["post"])
    async def post_no_body_no_resp() -> None:
        return

    @attrsapi.route("/post/201", quart=app, methods=["post"])
    async def post_201() -> tuple[str, Literal[201]]:
        return "test", 201

    @attrsapi.route("/post/multiple", quart=app, methods=["post"])
    async def post_multiple_codes() -> Union[
        tuple[str, Literal[200]], tuple[None, Literal[201]]
    ]:
        return None, 201

    @attrsapi.route("/put/cookie", quart=app, methods=["put"])
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    @attrsapi.route("/put/cookie-optional", quart=app, methods=["put"])
    async def put_cookie_optional(
        a_cookie: Annotated[Optional[str], Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    @attrsapi.delete("/delete/header", quart=app)
    async def delete_with_response_headers() -> tuple[None, Literal[204], dict]:
        return None, 204, {"response": "test"}

    @attrsapi.patch("/patch/cookie", quart=app)
    async def patch_with_response_cookies() -> tuple[None, Literal[200], dict]:
        return set_cookie((None, 200, {}), "cookie", "my_cookie", 1)

    return app


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
