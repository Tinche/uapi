from typing import Annotated, TypeAlias, TypeVar

from uapi import Cookie, Header, Method, ReqBody, ResponseException, RouteName
from uapi.base import App
from uapi.cookies import CookieSettings, set_cookie
from uapi.requests import HeaderSpec, JsonBodyLoader
from uapi.status import Created, Forbidden, NoContent, Ok

from .models import (
    GenericModel,
    ModelWithDict,
    ModelWithLiteral,
    NestedModel,
    ResponseGenericModel,
    ResponseGenericModelInner,
    ResponseGenericModelListInner,
    ResponseModel,
    SimpleModel,
    SumTypesRequestModel,
    SumTypesResponseModel,
)
from .models_2 import SimpleModel as SimpleModel2
from .response_classes import TooManyRequests

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
        """To be used as a description."""
        return "Hello, world"

    @app.post("/query-post")
    async def query_post(page: int) -> str:
        return str(page + 1)

    @app.get("/response-bytes", tags=["query"])
    async def response_bytes() -> bytes:
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

    @app.get("/throttled")
    async def throttled() -> Ok[None] | TooManyRequests[None]:
        return TooManyRequests(None)

    async def patch_attrs_union(
        test: str = "",
    ) -> Ok[NestedModel] | Created[SimpleModel]:
        return Ok(NestedModel()) if test != "1" else Created(SimpleModel(1))

    app.route("/patch/attrs", patch_attrs_union, methods=["PATCH"])

    @app.head("/head/exc")
    async def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

    @app.get("/exc/attrs")
    async def exception_attrs() -> None:
        """ResponseExceptions can have attrs classes."""
        raise ResponseException(Ok(SimpleModel()))

    @app.get("/exc/attrs-response")
    async def exception_attrs_response() -> Created:
        """ResponseExceptions can have attrs classes."""
        raise ResponseException(Ok(SimpleModel()))

    @app.get("/exc/attrs-none")
    async def exception_attrs_none():
        """ResponseExceptions can have attrs classes."""
        raise ResponseException(Ok(SimpleModel()))

    @app.put("/header")
    async def header(test_header: Header[str]) -> str:
        return test_header

    @app.put("/header-string-default")
    async def header_str_default(test_header: Header[str] = "def") -> str:
        """This is special-cased so needs a test."""
        return test_header

    @app.put("/header-default")
    async def header_default(test_header: Header[str | None] = None) -> str:
        return test_header or "default"

    @app.get("/header-renamed")
    async def header_renamed(
        test_header: Annotated[str, HeaderSpec("test_header")]
    ) -> str:
        return test_header

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
            NestedModel, JsonBodyLoader(error_handler=lambda e, _: Forbidden(str(e)))
        ]
    ) -> Ok[str]:
        """Custom validation error."""
        return Ok("")

    @app.get("/simple-model-2")
    async def simple_model_2() -> SimpleModel2:
        """OpenAPI should handle the same model name in different modules."""
        return SimpleModel2(1)

    @app.get("/literal-model")
    async def literal_model(m: ReqBody[ModelWithLiteral]) -> None:
        """OpenAPI should handle a model with a literal field."""
        return

    @app.post("/generic-model")
    async def generic_model(m: ReqBody[GenericModel[int]]) -> GenericModel[SimpleModel]:
        """OpenAPI should handle generic models."""
        return GenericModel(SimpleModel(1))

    @app.get("/response-model")
    async def response_model() -> ResponseModel:
        return ResponseModel([])

    @app.get("/response-generic-model")
    async def response_generic_model() -> ResponseGenericModel[
        ResponseGenericModelInner, ResponseGenericModelListInner
    ]:
        return ResponseGenericModel(ResponseGenericModelInner(1))

    @app.get("/response-union-nocontent")
    def response_union_nocontent(page: int = 0) -> Ok[SimpleModel] | NoContent:
        return Ok(SimpleModel()) if not page else NoContent()

    @app.get("/response-union-none")
    async def response_union_none(page: int = 0) -> Ok[SimpleModel] | Forbidden[None]:
        return Ok(SimpleModel()) if not page else Forbidden(None)

    @app.get("/sum-types-model")
    async def sum_types_model(
        payload: ReqBody[SumTypesRequestModel],
    ) -> SumTypesResponseModel:
        return SumTypesResponseModel(None)

    @app.post("/dictionary-models")
    async def dictionary_models(
        payload: ReqBody[dict[str, SimpleModel]]
    ) -> ModelWithDict:
        return ModelWithDict(payload)

    @app.get("/excluded")
    async def excluded() -> str:
        """This should be excluded from OpenAPI."""
        return ""

    # # Subapps.

    app.route_app(make_generic_subapp())
    app.route_app(make_generic_subapp(), "/subapp", "subapp")

    # A bit of dependency injection.
    def injected_id(header_for_injection: Header[str]) -> str:
        return f"injected:{header_for_injection}"

    app.incant.register_by_name(injected_id)

    @app.get("/injection")
    async def injection(injected_id: str) -> str:
        return injected_id

    # Route name composition.
    @app.get("/comp/route-name")
    @app.post("/comp/route-name", name="route-name-post")
    async def route_name(route_name: RouteName) -> str:
        return route_name

    # Request method composition.
    @app.get("/comp/req-method")
    @app.post("/comp/req-method", name="request-method-post")
    async def request_method(req_method: Method) -> str:
        return req_method


def configure_base_sync(app: App) -> None:
    @app.get("/")
    @app.post("/", name="hello-post")
    def hello() -> str:
        """To be used as a description."""
        return "Hello, world"

    @app.post("/query-post")
    def query_post(page: int) -> str:
        return str(page + 1)

    @app.get("/response-bytes", tags=["query"])
    def response_bytes() -> bytes:
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

    @app.get("/throttled")
    def throttled() -> Ok[None] | TooManyRequests[None]:
        return TooManyRequests(None)

    def patch_attrs_union(test: str = "") -> Ok[NestedModel] | Created[SimpleModel]:
        return Ok(NestedModel()) if test != "1" else Created(SimpleModel(1))

    app.route("/patch/attrs", patch_attrs_union, methods=["PATCH"])

    @app.head("/head/exc")
    def head_with_exc() -> str:
        raise ResponseException(Forbidden(None))

    @app.get("/exc/attrs")
    def exception_attrs() -> None:
        """ResponseExceptions can have attrs classes."""
        raise ResponseException(Ok(SimpleModel()))

    @app.get("/exc/attrs-response")
    def exception_attrs_response() -> Created[SimpleModel]:
        """ResponseExceptions can have attrs classes."""
        raise ResponseException(Ok(SimpleModel()))

    @app.get("/exc/attrs-none")
    def exception_attrs_none():
        """ResponseExceptions can have attrs classes."""
        raise ResponseException(Ok(SimpleModel()))

    @app.put("/header")
    def header(test_header: Header[str]) -> str:
        return test_header

    @app.put("/header-string-default")
    def header_str_default(test_header: Header[str] = "def") -> str:
        """This is special-cased so needs a test."""
        return test_header

    @app.put("/header-default")
    def header_default(test_header: Header[str | None] = None) -> str:
        return test_header or "default"

    @app.get("/header-renamed")
    def header_renamed(test_header: Annotated[str, HeaderSpec("test_header")]) -> str:
        return test_header

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
            NestedModel, JsonBodyLoader(error_handler=lambda e, _: Forbidden(str(e)))
        ]
    ) -> Ok[str]:
        """Custom validation error."""
        return Ok("")

    @app.get("/simple-model-2")
    def simple_model_2() -> SimpleModel2:
        """OpenAPI should handle the same model name in different modules."""
        return SimpleModel2(1)

    @app.get("/literal-model")
    def literal_model(m: ReqBody[ModelWithLiteral]) -> None:
        """OpenAPI should handle a model with a literal field."""
        return

    @app.post("/generic-model")
    def generic_model(m: ReqBody[GenericModel[int]]) -> GenericModel[SimpleModel]:
        """OpenAPI should handle generic models."""
        return GenericModel(SimpleModel(1))

    @app.get("/response-model")
    def response_model() -> ResponseModel:
        return ResponseModel([])

    @app.get("/response-generic-model")
    def response_generic_model() -> (
        ResponseGenericModel[ResponseGenericModelInner, ResponseGenericModelListInner]
    ):
        return ResponseGenericModel(ResponseGenericModelInner(1))

    @app.get("/response-union-nocontent")
    def response_union_nocontent(page: int = 0) -> Ok[SimpleModel] | NoContent:
        return Ok(SimpleModel()) if not page else NoContent()

    @app.get("/response-union-none")
    def response_union_none(page: int = 0) -> Ok[SimpleModel] | Forbidden[None]:
        return Ok(SimpleModel()) if not page else Forbidden(None)

    @app.get("/sum-types-model")
    def sum_types_model(
        payload: ReqBody[SumTypesRequestModel],
    ) -> SumTypesResponseModel:
        return SumTypesResponseModel(None)

    @app.post("/dictionary-models")
    def dictionary_models(payload: ReqBody[dict[str, SimpleModel]]) -> ModelWithDict:
        return ModelWithDict(payload)

    @app.get("/excluded")
    def excluded() -> str:
        """This should be excluded from OpenAPI."""
        return ""

    # Subapps.

    app.route_app(make_generic_subapp())
    app.route_app(make_generic_subapp(), "/subapp", "subapp")

    # A bit of dependency injection.
    def injected_id(header_for_injection: Header[str]) -> str:
        return f"injected:{header_for_injection}"

    app.incant.register_by_name(injected_id)

    @app.get("/injection")
    def injection(injected_id: str) -> str:
        return injected_id

    # Route name composition.
    @app.get("/comp/route-name")
    @app.post("/comp/route-name", name="route-name-post")
    def route_name(route_name: RouteName) -> str:
        return route_name

    # Request method composition.
    @app.get("/comp/req-method")
    @app.post("/comp/req-method", name="request-method-post")
    def request_method(req_method: Method) -> str:
        return req_method
