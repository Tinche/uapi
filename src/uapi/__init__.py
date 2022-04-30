from functools import partial
from typing import Any, Callable, Optional, Sequence

from attrs import Factory, define, frozen
from cattrs import Converter
from cattrs.preconf.orjson import make_converter
from incant import Incanter
from orjson import dumps

from .cookies import Cookie
from .openapi import OpenAPI
from .openapi import converter as openapi_converter
from .openapi import make_openapi_spec
from .status import BaseResponse, Found, Headers, Ok, SeeOther
from .types import PathParamParser

__all__ = ["Cookie", "make_base_incanter", "App"]


@frozen
class Header:
    name: str


def make_base_incanter() -> Incanter:
    """Create the base (non-framework) incanter."""
    res = Incanter()
    return res


@define
class App:
    framework_incant: Incanter
    converter: Converter = Factory(make_converter)
    base_incant: Incanter = Factory(make_base_incanter)
    route_map: dict[tuple[str, str], tuple[Callable, Optional[str]]] = Factory(dict)
    _path_param_parser: PathParamParser = lambda p: (p, [])
    _framework_resp_cls = None

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

    def make_openapi_spec(self) -> OpenAPI:
        return make_openapi_spec(
            self.route_map,
            self._path_param_parser,
            framework_resp_cls=self._framework_resp_cls,
        )

    def serve_openapi(self, path: str = "/openapi.json"):
        openapi = self.make_openapi_spec()
        payload = openapi_converter.unstructure(openapi)

        def openapi_handler() -> Ok[bytes]:
            return Ok(dumps(payload), {"content-type": "application/json"})

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


def redirect(location: str, headers: Headers = {}) -> Found[None]:
    return Found(None, headers | {"Location": location})


def redirect_to_get(location: str, headers: Headers = {}) -> SeeOther[None]:
    return SeeOther(None, headers | {"Location": location})


@define
class ResponseException(Exception):
    """An exception that is converted into an HTTP response."""

    response: BaseResponse
