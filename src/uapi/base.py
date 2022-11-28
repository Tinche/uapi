from functools import partial
from types import NoneType
from typing import Any, Callable, ClassVar, Optional, Sequence

from attrs import Factory, define
from cattrs import Converter
from cattrs.preconf.orjson import make_converter
from incant import Incanter
from orjson import dumps

from .openapi import OpenAPI
from .openapi import converter as openapi_converter
from .openapi import make_openapi_spec
from .status import Ok
from .types import PathParamParser


def make_base_incanter() -> Incanter:
    """Create the base (non-framework) incanter."""
    res = Incanter()
    return res


@define
class App:
    converter: Converter = Factory(make_converter)
    base_incant: Incanter = Factory(make_base_incanter)
    route_map: dict[tuple[str, str], tuple[Callable, Optional[str]]] = Factory(dict)
    _path_param_parser: PathParamParser = lambda p: (p, [])
    _framework_resp_cls: ClassVar[type] = NoneType

    def route(
        self,
        path: str,
        handler,
        name: Optional[str] = None,
        methods: Sequence[str] = ["GET"],
    ):
        """Register routes. This is not a decorator."""
        for method in methods:
            self.route_map[(method.upper(), path)] = (handler, name)
        return handler

    def get(self, path: str, name: Optional[str] = None):
        return partial(self.route, path, name=name, methods=["GET"])

    def post(self, path: str, name: Optional[str] = None):
        return partial(self.route, path, name=name, methods=["POST"])

    def put(self, path: str, name: Optional[str] = None):
        return partial(self.route, path, name=name, methods=["PUT"])

    def patch(self, path: str, name: Optional[str] = None):
        return partial(self.route, path, name=name, methods=["PATCH"])

    def delete(self, path: str, name: Optional[str] = None):
        return partial(self.route, path, name=name, methods=["DELETE"])

    def head(self, path: str, name: Optional[str] = None):
        return partial(self.route, path, name=name, methods=["HEAD"])

    def options(self, path: str, name: Optional[str] = None):
        return partial(self.route, path, name=name, methods=["OPTIONS"])

    def route_app(
        self, app: "App", prefix: str | None = None, name_prefix: str | None = None
    ) -> None:
        """Register all routes from a different app under an optional path prefix."""
        if not isinstance(self, type(app)):
            raise Exception("Incompatible apps.")
        for (method, path), (handler, name) in app.route_map.items():
            if name_prefix is not None:
                if name is None:
                    name = handler.__name__
                name = f"{name_prefix}.{name}"
            self.route_map[(method, (prefix or "") + path)] = (handler, name)

    def make_openapi_spec(self) -> OpenAPI:
        return make_openapi_spec(
            self.route_map,
            self._path_param_parser,
            framework_resp_cls=self._framework_resp_cls,
        )

    def serve_openapi(self, path: str = "/openapi.json"):
        openapi = self.make_openapi_spec()
        payload = dumps(openapi_converter.unstructure(openapi))

        def openapi_handler() -> Ok[bytes]:
            return Ok(payload, {"content-type": "application/json"})

        self.route(path, openapi_handler)

    def serve_swaggerui(self, path: str = "/swaggerui"):
        from .swaggerui import swaggerui

        def swaggerui_handler() -> Ok[str]:
            return Ok(swaggerui, {"content-type": "text/html"})

        self.route(path, swaggerui_handler)

    def serve_redoc(self, path: str = "/redoc"):
        from .swaggerui import redoc

        def redoc_handler() -> Ok[str]:
            return Ok(redoc, {"content-type": "text/html"})

        self.route(path, redoc_handler)

    def serve_elements(self, path: str = "/elements", **kwargs: Any):
        from .swaggerui import elements

        def handler() -> Ok[str]:
            return Ok(elements, {"content-type": "text/html"})

        self.route(path, handler)
