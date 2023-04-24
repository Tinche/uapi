from django.http import HttpRequest as Request
from django.http import HttpResponse as Response

from uapi import ResponseException
from uapi.django import App
from uapi.status import NoContent

from ..apps import configure_base_sync

app = App()

configure_base_sync(app)


class DjangoRespSubclass(Response):
    pass


@app.get("/framework-request")
def framework_request(req: Request) -> str:
    return "framework_request" + req.headers["test"]


@app.post("/framework-resp-subclass")
def framework_resp_subclass() -> DjangoRespSubclass:
    return DjangoRespSubclass("framework_resp_subclass", status=201)


def path(path_id: int) -> Response:
    return Response(str(path_id + 1))


app.route("/path/<int:path_id>", path)


@app.options("/unannotated-exception")
def unannotated_exception() -> Response:
    raise ResponseException(NoContent())


@app.get("/query/unannotated", tags=["query"])
def query_unannotated(query) -> Response:
    return Response(query + "suffix")


@app.get("/query/string", tags=["query"])
def query_string(query: str) -> Response:
    return Response(query + "suffix")


@app.get("/query", tags=["query"])
def query(page: int) -> Response:
    return Response(str(page + 1))


@app.get("/query-default", tags=["query"])
def query_default(page: int = 0) -> Response:
    return Response(str(page + 1))


@app.post("/post/no-body-native-response")
def post_no_body() -> Response:
    return Response("post", status=201)


@app.post("/path1/<path_id>")
def post_path_string(path_id: str) -> str:
    return str(int(path_id) + 2)


# This is difficult to programatically set, so just always run it.
app.serve_openapi()
