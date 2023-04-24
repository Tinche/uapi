from functools import partial
from types import NoneType
from typing import Callable, ClassVar, Sequence

from attrs import Factory, define
from cattrs import Converter
from cattrs.preconf.orjson import make_converter
from incant import Incanter
from orjson import dumps

from .openapi import ApiKeySecurityScheme, OpenAPI, SummaryTransformer
from .openapi import converter as openapi_converter
from .openapi import default_summary_transformer, make_openapi_spec
from .status import Ok
from .types import Method, PathParamParser, RouteName, RouteTags


def make_base_incanter() -> Incanter:
    """Create the base (non-framework) incanter."""
    res = Incanter()
    return res


@define
class OpenAPISecuritySpec:
    security_scheme: ApiKeySecurityScheme


@define
class App:
    converter: Converter = Factory(make_converter)
    base_incant: Incanter = Factory(make_base_incanter)
    _route_map: dict[
        tuple[Method, str], tuple[Callable, RouteName, RouteTags]
    ] = Factory(dict)
    _openapi_security: list[OpenAPISecuritySpec] = Factory(list)
    _path_param_parser: ClassVar[PathParamParser] = lambda p: (p, [])
    _framework_req_cls: ClassVar[type] = NoneType
    _framework_resp_cls: ClassVar[type] = NoneType

    def route(
        self,
        path: str,
        handler,
        methods: Sequence[Method] = ["GET"],
        name: str | None = None,
        tags: RouteTags = (),
    ):
        """Register routes. This is not a decorator.

        :param tags: The OpenAPI tags to apply.
        """
        if name is None:
            name = handler.__name__
        for method in methods:
            self._route_map[(method, path)] = (handler, name, tags)
        return handler

    def get(self, path: str, name: str | None = None, tags: RouteTags = ()):
        return partial(self.route, path, name=name, methods=["GET"], tags=tags)

    def post(self, path: str, name: str | None = None, tags: RouteTags = ()):
        return partial(self.route, path, name=name, methods=["POST"], tags=tags)

    def put(self, path: str, name: str | None = None, tags: RouteTags = ()):
        return partial(self.route, path, name=name, methods=["PUT"], tags=tags)

    def patch(self, path: str, name: str | None = None, tags: RouteTags = ()):
        return partial(self.route, path, name=name, methods=["PATCH"], tags=tags)

    def delete(self, path: str, name: str | None = None, tags: RouteTags = ()):
        return partial(self.route, path, name=name, methods=["DELETE"], tags=tags)

    def head(self, path: str, name: str | None = None, tags: RouteTags = ()):
        return partial(self.route, path, name=name, methods=["HEAD"], tags=tags)

    def options(self, path: str, name: str | None = None, tags: RouteTags = ()):
        return partial(self.route, path, name=name, methods=["OPTIONS"], tags=tags)

    def route_app(
        self, app: "App", prefix: str | None = None, name_prefix: str | None = None
    ) -> None:
        """Register all routes from a different app under an optional path prefix."""
        if not isinstance(self, type(app)):
            raise Exception("Incompatible apps.")
        for (method, path), (handler, name, tags) in app._route_map.items():
            if name_prefix is not None:
                if name is None:
                    name = handler.__name__
                name = f"{name_prefix}.{name}"
            self._route_map[(method, (prefix or "") + path)] = (handler, name, tags)

    def make_openapi_spec(
        self,
        title: str = "Server",
        version: str = "1.0",
        exclude: set[RouteName] = set(),
        summary_transformer: SummaryTransformer = default_summary_transformer,
    ) -> OpenAPI:
        """
        Create the OpenAPI spec for the registered routes.

        :param exclude: A set of route names to exclude from the spec.
        :param summary_transformer: A function to map handlers and
            route names to OpenAPI PathItem summary strings.
        """
        # We need to prepare the handlers to get the correct signature.
        route_map = {
            k: (self.base_incant.prepare(v[0]), v[1], v[2])
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
            [s.security_scheme for s in self._openapi_security],
            summary_transformer,
        )

    def serve_openapi(
        self,
        title: str = "Server",
        path: str = "/openapi.json",
        exclude: set[str] = set(),
        summary_transformer: SummaryTransformer = default_summary_transformer,
    ):
        """
        Create the OpenAPI spec and start serving it at the given path.

        :param exclude: A set of route names to exclude from the spec.
        :param summary_transformer: A function to map handlers and
            route names to OpenAPI PathItem summary strings.
        """
        openapi = self.make_openapi_spec(
            title, exclude=exclude, summary_transformer=summary_transformer
        )
        payload = dumps(openapi_converter.unstructure(openapi))

        def openapi_handler() -> Ok[bytes]:
            return Ok(payload, {"content-type": "application/json"})

        self.route(path, openapi_handler)

    def serve_swaggerui(self, path: str = "/swaggerui"):
        from .openapi_ui import swaggerui

        def swaggerui_handler() -> Ok[str]:
            return Ok(swaggerui, {"content-type": "text/html"})

        self.route(path, swaggerui_handler)

    def serve_redoc(self, path: str = "/redoc"):
        from .openapi_ui import redoc

        def redoc_handler() -> Ok[str]:
            return Ok(redoc, {"content-type": "text/html"})

        self.route(path, redoc_handler)

    def serve_elements(
        self, path: str = "/elements", openapi_path: str = "/openapi.json"
    ):
        from .openapi_ui import elements as elements_html

        fixed_path = elements_html.replace("$OPENAPIURL", openapi_path)

        def elements() -> Ok[str]:
            return Ok(fixed_path, {"content-type": "text/html"})

        self.route(path, elements)
