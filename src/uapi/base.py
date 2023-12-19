from collections.abc import Callable, Coroutine, Iterable, Sequence
from functools import partial
from types import NoneType
from typing import Any, ClassVar, Final, Generic, TypeAlias, TypeVar

from attrs import AttrsInstance, Factory, define, field
from cattrs import Converter
from cattrs.preconf.orjson import make_converter
from incant import Incanter
from orjson import dumps

from ._openapi import (
    DescriptionTransformer,
    SummaryTransformer,
    default_description_transformer,
    default_summary_transformer,
    make_openapi_spec,
)
from .openapi import ApiKeySecurityScheme, OpenAPI
from .openapi import converter as openapi_converter
from .shorthands import (
    BytesShorthand,
    NoneShorthand,
    ResponseShorthand,
    StrShorthand,
    T_co,
    make_attrs_shorthand,
)
from .status import BaseResponse, Ok
from .types import Method, RouteName, RouteTags

__all__ = ["App"]


@define
class OpenAPISecuritySpec:
    security_scheme: ApiKeySecurityScheme


C = TypeVar("C")
H = TypeVar("H", bound=Callable[..., Any])

default_shorthands: Final = (NoneShorthand, StrShorthand, BytesShorthand)


def make_default_shorthands(converter: Converter) -> Sequence[type[ResponseShorthand]]:
    return (*default_shorthands, make_attrs_shorthand(converter))


@define
class _AppBase:
    """The common base for sync and async apps."""

    converter: Converter = Factory(make_converter)
    #: The incanter used to compose handlers and middleware.
    incant: Incanter = Factory(Incanter)
    _route_map: dict[
        tuple[Method, str], tuple[Callable, RouteName, RouteTags]
    ] = Factory(dict)
    _openapi_security: list[OpenAPISecuritySpec] = Factory(list)
    _shorthands: Sequence[type[ResponseShorthand]] = field(
        default=Factory(
            lambda self: make_default_shorthands(self.converter), takes_self=True
        ),
        init=False,
    )
    _framework_req_cls: ClassVar[type] = NoneType
    _framework_resp_cls: ClassVar[type] = NoneType

    @staticmethod
    def _path_param_parser(p: str) -> tuple[str, list[str]]:
        """Override me with your path param parsing."""
        return (p, [])

    def route_app(
        self, app: "App", prefix: str | None = None, name_prefix: str | None = None
    ) -> None:
        """Register all routes from a different app under an optional path prefix."""
        if not type(app) == App:
            raise Exception("Incompatible apps.")
        for (method, path), (handler, name, tags) in app._route_map.items():
            if name_prefix is not None:
                name = RouteName(f"{name_prefix}.{name}")
            self._route_map[(method, (prefix or "") + path)] = (handler, name, tags)

    def make_openapi_spec(
        self,
        title: str = "Server",
        version: str = "1.0",
        exclude: set[str] = set(),
        summary_transformer: SummaryTransformer = default_summary_transformer,
        description_transformer: DescriptionTransformer = default_description_transformer,
    ) -> OpenAPI:
        """
        Create the OpenAPI spec for the registered routes.

        :param title: The OpenAPI info title.
        :param version: The OpenAPI info version.
        :param exclude: A set of route names to exclude from the spec.
        :param summary_transformer: A function to map handlers and
            route names to OpenAPI PathItem summary strings.
        :param description_transformer: A function to map handlers
            and route names to OpenAPI PathItem description strings.
        """
        # We need to prepare the handlers to get the correct signature.
        route_map = {
            k: (self.incant.compose(v[0]), v[0], v[1], v[2])
            for k, v in self._route_map.items()
            if v[1] not in exclude
        }
        return make_openapi_spec(
            route_map,
            self.__class__._path_param_parser,
            title,
            version,
            self._framework_req_cls,
            self._framework_resp_cls,
            self._shorthands,
            [s.security_scheme for s in self._openapi_security],
            summary_transformer,
            description_transformer,
        )

    def serve_openapi(
        self,
        title: str = "Server",
        path: str = "/openapi.json",
        exclude: set[str] = set(),
        summary_transformer: SummaryTransformer = default_summary_transformer,
        description_transformer: DescriptionTransformer = default_description_transformer,
    ):
        """
        Create the OpenAPI spec and start serving it at the given path.

        :param exclude: A set of route names to exclude from the spec.
        :param summary_transformer: A function to map handlers and
            route names to OpenAPI PathItem summary strings.
        :param description_transformer: A function to map handlers
            and route names to OpenAPI PathItem description strings.
        """
        openapi = self.make_openapi_spec(
            title,
            exclude=exclude,
            summary_transformer=summary_transformer,
            description_transformer=description_transformer,
        )
        payload = dumps(openapi_converter.unstructure(openapi))

        def openapi_handler() -> Ok[bytes]:
            return Ok(payload, {"content-type": "application/json"})

        self._route_map[("GET", path)] = (
            openapi_handler,
            RouteName("openapi_handler"),
            (),
        )

    def serve_swaggerui(
        self, path: str = "/swaggerui", openapi_path: str = "/openapi.json"
    ):
        """Start serving the Swagger UI at the given path."""
        from .openapi_ui import swaggerui

        fixed_path = swaggerui.replace("$OPENAPIURL", openapi_path)

        def swaggerui_handler() -> Ok[str]:
            return Ok(fixed_path, {"content-type": "text/html"})

        self._route_map[("GET", path)] = (
            swaggerui_handler,
            RouteName("swaggerui_handler"),
            (),
        )

    def serve_redoc(self, path: str = "/redoc", openapi_path: str = "/openapi.json"):
        """Start serving the ReDoc UI at the given path."""
        from .openapi_ui import redoc

        fixed_path = redoc.replace("$OPENAPIURL", openapi_path)

        def redoc_handler() -> Ok[str]:
            return Ok(fixed_path, {"content-type": "text/html"})

        self._route_map[("GET", path)] = (redoc_handler, RouteName("redoc_handler"), ())

    def serve_elements(
        self, path: str = "/elements", openapi_path: str = "/openapi.json"
    ):
        """Start serving the OpenAPI Elements UI at the given path."""
        from .openapi_ui import elements as elements_html

        fixed_path = elements_html.replace("$OPENAPIURL", openapi_path)

        def elements() -> Ok[str]:
            return Ok(fixed_path, {"content-type": "text/html"})

        self._route_map[("GET", path)] = (elements, RouteName("elements"), ())


DefaultReturns: TypeAlias = BaseResponse | None | str | bytes | AttrsInstance


@define
class App(Generic[C], _AppBase):
    """A base _uapi_ synchronous App.

    Use this class directly when creating reusable apps, or subclass
    it to create a framework-specific app.

    Otherwise, an existing framework-specific app should be used.
    """

    def route(
        self,
        path: str,
        handler: Callable[..., DefaultReturns | C],
        methods: Iterable[Method] = {"GET"},
        name: str | None = None,
        tags: RouteTags = (),
    ) -> Any:
        """Register routes. This is not a decorator.

        :param path: The URL path on which to serve the handler.
        :param handler: The handler to route to.
        :param methods: The HTTP methods on which to serve the handler.
        :param name: The route name. If not provided, will use the handler name.
        :param tags: The OpenAPI tags to apply.
        """
        if name is None:
            name = handler.__name__
        for method in methods:
            self._route_map[(method, path)] = (handler, RouteName(name), tags)
        return handler

    def get(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[[Callable[..., DefaultReturns | C]], Any]:
        return partial(self.route, path, name=name, methods=["GET"], tags=tags)

    def post(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[[Callable[..., DefaultReturns | C]], Any]:
        return partial(self.route, path, name=name, methods=["POST"], tags=tags)

    def put(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[[Callable[..., DefaultReturns | C]], Any]:
        return partial(self.route, path, name=name, methods=["PUT"], tags=tags)

    def patch(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[[Callable[..., DefaultReturns | C]], Any]:
        return partial(self.route, path, name=name, methods=["PATCH"], tags=tags)

    def delete(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[[Callable[..., DefaultReturns | C]], Any]:
        return partial(self.route, path, name=name, methods=["DELETE"], tags=tags)

    def head(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[[Callable[..., DefaultReturns | C]], Any]:
        return partial(self.route, path, name=name, methods=["HEAD"], tags=tags)

    def options(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[[Callable[..., DefaultReturns | C]], Any]:
        return partial(self.route, path, name=name, methods=["OPTIONS"], tags=tags)

    def add_response_shorthand(
        self, shorthand: type[ResponseShorthand[T_co]]
    ) -> "App[C | T_co]":
        """Add a response shorthand to the App.

        Response shorthands enable additional return types for handlers.

        The type will be matched by identity and an `is_subclass` check.

        :param type: The type to add to possible handler return annotations.
        :param response_adapter: A callable, used to convert a value of the new type
            into a `BaseResponse`.
        """
        self._shorthands = (*self._shorthands, shorthand)
        return self  # type: ignore


class AsyncApp(Generic[C], _AppBase):
    """Override type signatures for handlers."""

    def route(
        self,
        path: str,
        handler: Callable[
            ..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]
        ],
        methods: Iterable[Method] = {"GET"},
        name: str | None = None,
        tags: RouteTags = (),
    ) -> Any:
        """Register routes. This is not a decorator.

        :param path: The URL path on which to serve the handler.
        :param handler: The handler to route to.
        :param methods: The HTTP methods on which to serve the handler.
        :param name: The route name. If not provided, will use the handler name.
        :param tags: The OpenAPI tags to apply.
        """
        if name is None:
            name = handler.__name__
        for method in methods:
            self._route_map[(method, path)] = (handler, RouteName(name), tags)
        return handler

    def get(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[
        [Callable[..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]]],
        Any,
    ]:
        return partial(self.route, path, name=name, methods=["GET"], tags=tags)

    def post(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[
        [Callable[..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]]],
        Any,
    ]:
        return partial(self.route, path, name=name, methods=["POST"], tags=tags)

    def put(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[
        [Callable[..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]]],
        Any,
    ]:
        return partial(self.route, path, name=name, methods=["PUT"], tags=tags)

    def patch(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[
        [Callable[..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]]],
        Any,
    ]:
        return partial(self.route, path, name=name, methods=["PATCH"], tags=tags)

    def delete(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[
        [Callable[..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]]],
        Any,
    ]:
        return partial(self.route, path, name=name, methods=["DELETE"], tags=tags)

    def head(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[
        [Callable[..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]]],
        Any,
    ]:
        return partial(self.route, path, name=name, methods=["HEAD"], tags=tags)

    def options(
        self, path: str, name: str | None = None, tags: RouteTags = ()
    ) -> Callable[
        [Callable[..., DefaultReturns | C | Coroutine[None, None, DefaultReturns | C]]],
        Any,
    ]:
        return partial(self.route, path, name=name, methods=["OPTIONS"], tags=tags)

    def add_response_shorthand(
        self, shorthand: type[ResponseShorthand[T_co]]
    ) -> "AsyncApp[C | T_co]":
        """Add a response shorthand to the App.

        Response shorthands enable additional return types for handlers.

        The type will be matched by identity and an `is_subclass` check.

        :param type: The type to add to possible handler return annotations.
        :param response_adapter: A callable, used to convert a value of the new type
            into a `BaseResponse`.
        """
        self._shorthands = (*self._shorthands, shorthand)
        return self  # type: ignore
