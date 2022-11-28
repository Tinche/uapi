from typing import Annotated, TypeAlias, TypeVar

from uapi import Cookie, ReqBody, ResponseException
from uapi.base import App
from uapi.cookies import CookieSettings, set_cookie
from uapi.requests import JsonBodyLoader
from uapi.status import Created, Forbidden, NoContent, Ok

from .models import NestedModel, SimpleModel

T = TypeVar("T")
CustomReqBody: TypeAlias = Annotated[T, JsonBodyLoader("application/vnd.uapi.v1+json")]


def make_generic_subapp() -> App:
    app = App()

    @app.get("/subapp")
    def subapp() -> str:
        return "subapp"

    return app


def configure_base_async(app: App) -> None:
    @app.get("/")
    @app.post("/", name="hello-post")
    async def hello() -> str:
        return "Hello, world"

    @app.get("/query-bytes")
    async def query_bytes() -> bytes:
        return b"2"

    @app.get("/get/model")
    async def get_model() -> NestedModel:
        return NestedModel()

    @app.get("/get/model-status")
    async def get_model_status() -> Created[NestedModel]:
        return Created(NestedModel(), {"test": "test"})

    async def post_no_body_no_response() -> None:
        return

    app.route("/post/no-body-no-response", post_no_body_no_response, methods=["POST"])

    @app.post("/post/201")
    async def post_201() -> Created[str]:
        return Created("test")

    @app.post("/post/multiple")
    async def post_multiple_codes() -> Ok[str] | Created[None]:
        return Created(None)

    @app.post("/post/model")
    async def post_model(body: ReqBody[NestedModel]) -> Created[NestedModel]:
        return Created(body)

    @app.put("/put/cookie")
    async def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    async def put_cookie_optional(
        a_cookie: Annotated[str | None, Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    app.route("/put/cookie-optional", put_cookie_optional, methods=["PUT"])

    @app.delete("/delete/header")
    async def delete_with_response_headers() -> NoContent:
        return NoContent({"response": "test"})

    @app.patch("/patch/cookie")
    async def patch_with_response_cookies() -> Ok[None]:
        return Ok(None, set_cookie("cookie", "my_cookie", CookieSettings(max_age=1)))

    async def patch_attrs_union() -> NestedModel | Created[SimpleModel]:
        return NestedModel()

    app.route("/patch/attrs", patch_attrs_union, methods=["patch"])

    @app.head("/head/exc")
    async def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

    @app.put("/custom-loader")
    async def custom_loader(body: CustomReqBody[NestedModel]) -> Ok[str]:
        return Ok(str(body.simple_model.an_int))

    @app.patch("/custom-loader-no-ct")
    async def custom_loader_no_ct(
        body: Annotated[NestedModel, JsonBodyLoader(None)]
    ) -> Ok[str]:
        """No content-type required."""
        return Ok(str(body.simple_model.an_int + 1))

    @app.post("/custom-loader-error")
    async def custom_loader_error(
        body: Annotated[
            NestedModel, JsonBodyLoader(error_handler=lambda e, _: Forbidden(str(e))),
        ]
    ) -> Ok[str]:
        """Custom validation error."""
        return Ok("")

    # Subapps.

    app.route_app(make_generic_subapp())
    app.route_app(make_generic_subapp(), "/subapp", "subapp")


def configure_base_sync(app: App) -> None:
    @app.get("/")
    @app.post("/", name="hello-post")
    def hello() -> str:
        return "Hello, world"

    @app.get("/query-bytes")
    def query_bytes() -> bytes:
        return b"2"

    @app.get("/get/model")
    def get_model() -> NestedModel:
        return NestedModel()

    @app.get("/get/model-status")
    def get_model_status() -> Created[NestedModel]:
        return Created(NestedModel(), {"test": "test"})

    def post_no_body_no_response() -> None:
        return

    app.route("/post/no-body-no-response", post_no_body_no_response, methods=["POST"])

    @app.post("/post/201")
    def post_201() -> Created[str]:
        return Created("test")

    @app.post("/post/multiple")
    def post_multiple_codes() -> Ok[str] | Created[None]:
        return Created(None)

    @app.post("/post/model")
    def post_model(body: ReqBody[NestedModel]) -> Created[NestedModel]:
        return Created(body)

    @app.put("/put/cookie")
    def put_cookie(a_cookie: Cookie) -> str:
        return a_cookie

    def put_cookie_optional(
        a_cookie: Annotated[str | None, Cookie("A-COOKIE")] = None
    ) -> str:
        return a_cookie if a_cookie is not None else "missing"

    app.route("/put/cookie-optional", put_cookie_optional, methods=["PUT"])

    @app.delete("/delete/header")
    def delete_with_response_headers() -> NoContent:
        return NoContent({"response": "test"})

    @app.patch("/patch/cookie")
    def patch_with_response_cookies() -> Ok[None]:
        return Ok(None, set_cookie("cookie", "my_cookie", CookieSettings(max_age=1)))

    def patch_attrs_union() -> NestedModel | Created[SimpleModel]:
        return NestedModel()

    app.route("/patch/attrs", patch_attrs_union, methods=["patch"])

    @app.head("/head/exc")
    def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

    @app.put("/custom-loader")
    def custom_loader(body: CustomReqBody[NestedModel]) -> Ok[str]:
        return Ok(str(body.simple_model.an_int))

    @app.patch("/custom-loader-no-ct")
    def custom_loader_no_ct(
        body: Annotated[NestedModel, JsonBodyLoader(None)]
    ) -> Ok[str]:
        """No content-type required."""
        return Ok(str(body.simple_model.an_int + 1))

    @app.post("/custom-loader-error")
    def custom_loader_error(
        body: Annotated[
            NestedModel, JsonBodyLoader(error_handler=lambda e, _: Forbidden(str(e))),
        ]
    ) -> Ok[str]:
        """Custom validation error."""
        return Ok("")

    # Subapps.

    app.route_app(make_generic_subapp())
    app.route_app(make_generic_subapp(), "/subapp", "subapp")
