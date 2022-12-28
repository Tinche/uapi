from aiohttp import web
from aiohttp.web import Request, Response

from uapi import ResponseException
from uapi.aiohttp import App
from uapi.status import NoContent

from .apps import configure_base_async


class RespSubclass(Response):
    pass


def make_app() -> App:
    app = App()

    @app.get("/framework-request")
    async def framework_request(req: Request) -> str:
        return "framework_request" + req.headers["test"]

    @app.post("/framework-resp-subclass")
    async def framework_resp_subclass() -> RespSubclass:
        return RespSubclass(body="framework_resp_subclass", status=201)

    async def path_param(path_id: int) -> Response:
        return Response(text=str(path_id + 1))

    app.route("/path/{path_id}", path_param)

    configure_base_async(app)

    @app.options("/unannotated-exception")
    async def unannotated_exception() -> Response:
        raise ResponseException(NoContent())

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

    @app.post("/post/no-body-native-response")
    async def post_no_body() -> Response:
        return Response(text="post", status=201)

    @app.post("/path1/{path_id}")
    async def post_path_string(path_id: str) -> str:
        return str(int(path_id) + 2)

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
