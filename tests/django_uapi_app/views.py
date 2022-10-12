from typing import Annotated, Optional, Union

from django.http import HttpResponse

from uapi import Cookie, ReqBody, ResponseException
from uapi.cookies import CookieSettings, set_cookie
from uapi.django import App
from uapi.status import Created, Forbidden, NoContent, Ok

from ..apps import make_generic_subapp
from ..models import NestedModel, SimpleModel

# Create your views here.
app = App()


@app.get("/")
@app.post("/", name="hello-post")
def hello() -> str:
    return "Hello, world"


def path(path_id: int) -> HttpResponse:
    return HttpResponse(str(path_id + 1))


app.route("/path/<int:path_id>", path)


@app.get("/query/unannotated")
def query_unannotated(query) -> HttpResponse:
    return HttpResponse(query + "suffix")


@app.get("/query/string")
def query_string(query: str) -> HttpResponse:
    return HttpResponse(query + "suffix")


@app.get("/query")
def query(page: int) -> HttpResponse:
    return HttpResponse(str(page + 1))


@app.get("/query-default")
def query_default(page: int = 0) -> HttpResponse:
    return HttpResponse(str(page + 1))


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
def post_no_body() -> HttpResponse:
    return HttpResponse("post", status=201)


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
def post_model(body: ReqBody[NestedModel]) -> Created[NestedModel]:
    return Created(body)


@app.post("/path1/<path_id>")
def post_path_string(path_id: str) -> str:
    return str(int(path_id) + 2)


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


app.route_app(make_generic_subapp())
app.route_app(make_generic_subapp(), "/subapp", "subapp")

# This is difficult to programatically set, so just always run it.
app.serve_openapi()
