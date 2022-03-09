from abc import abstractmethod

from attrs import Factory, define, frozen
from cattrs import Converter
from cattrs.preconf.ujson import make_converter
from incant import Incanter

from .cookies import Cookie
from .status import BaseResponse, Found, Headers, Ok, SeeOther

__all__ = ["Cookie", "make_base_incanter", "BaseApp"]


@frozen
class Header:
    name: str


def make_base_incanter() -> Incanter:
    """Create the base (non-framework) incanter."""
    res = Incanter()
    return res


@define
class BaseApp:
    framework_incant: Incanter
    converter: Converter = Factory(make_converter)
    base_incant: Incanter = Factory(make_base_incanter)

    def serve_swaggerui(self, path: str = "/swaggerui"):
        from .swaggerui import swaggerui

        async def swaggerui_handler() -> Ok[str]:
            return Ok(swaggerui, {"content-type": "text/html"})

        self.route(path)(swaggerui_handler)

    def serve_redoc(self, path: str = "/redoc"):
        from .swaggerui import redoc

        async def redoc_handler() -> Ok[str]:
            return Ok(redoc, {"content-type": "text/html"})

        self.route(path)(redoc_handler)

    @abstractmethod
    def route(self, path: str):
        raise NotImplementedError


def redirect(location: str, headers: Headers = {}) -> Found[None]:
    return Found(None, headers | {"Location": location})


def redirect_to_get(location: str, headers: Headers = {}) -> SeeOther[None]:
    return SeeOther(None, headers | {"Location": location})


@define
class ResponseException(Exception):
    """An exception that is converted into an HTTP response."""

    response: BaseResponse
