from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from uapi import Method, ResponseException, RouteName
from uapi.starlette import App
from uapi.status import NoContent

from .apps import configure_base_async


def make_app() -> App:
    app = App()
    configure_base_async(app)

    @app.get("/framework-request")
    async def framework_request(req: Request) -> str:
        return "framework_request" + req.headers["test"]

    @app.post("/framework-resp-subclass")
    async def framework_resp_subclass() -> PlainTextResponse:
        return PlainTextResponse("framework_resp_subclass", status_code=201)

    async def path(path_id: int) -> Response:
        return Response(str(path_id + 1))

    app.route("/path/{path_id}", path)

    @app.options("/unannotated-exception")
    async def unannotated_exception() -> Response:
        raise ResponseException(NoContent())

    @app.post("/post/no-body-native-response")
    async def post_no_body() -> Response:
        return Response("post", 201)

    @app.get("/query/unannotated", tags=["query"])
    async def query_unannotated(query) -> Response:
        return Response(query + "suffix")

    @app.get("/query/string", tags=["query"])
    async def query_string(query: str) -> Response:
        return Response(query + "suffix")

    @app.get("/query", tags=["query"])
    async def query(page: int) -> Response:
        return Response(str(page + 1))

    @app.get("/query-default", tags=["query"])
    async def query_default(page: int = 0) -> Response:
        return Response(str(page + 1))

    @app.post("/path1/{path_id}")
    async def post_path_string(path_id: str) -> str:
        return str(int(path_id) + 2)

    # Route name composition.
    @app.get("/comp/route-name-native")
    @app.post("/comp/route-name-native", name="route-name-native-post")
    def route_name_native(route_name: RouteName) -> Response:
        return Response(route_name)

    # Request method composition.
    @app.get("/comp/req-method-native")
    @app.post("/comp/req-method-native", name="request-method-native-post")
    def request_method_native(req_method: Method) -> Response:
        return Response(req_method)

    return app


async def run_on_starlette(app: App, port: int) -> None:
    await app.run(port, handle_signals=False)
