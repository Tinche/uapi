from typing import Callable, Literal, Optional, Union

from attrs import Factory, define, frozen
from cattrs import Converter, GenConverter
from incant import Incanter


@frozen
class Header:
    name: str


@frozen
class Cookie:
    name: Optional[str] = None


Parameter = Union[Header]


def parameters(**kwargs: Parameter) -> Callable[[Callable], Callable]:
    def inner(fn: Callable) -> Callable:
        fn.__attrs_api_meta__ = kwargs  # type: ignore
        return fn

    return inner


def make_base_incanter() -> Incanter:
    """Create the base (non-framework) incanter."""
    res = Incanter()
    return res


@define
class BaseApp:
    framework_incant: Incanter
    converter: Converter = Factory(GenConverter)
    base_incant: Incanter = Factory(make_base_incanter)

    def serve_swaggerui(self):
        from .swaggerui import swaggerui

        async def swaggerui_handler() -> tuple[str, Literal[200], dict]:
            return swaggerui, 200, {"content-type": "text/html"}

        self.route("/swaggerui")(swaggerui_handler)

    def serve_redoc(self):
        from .swaggerui import redoc

        async def redoc_handler() -> tuple[str, Literal[200], dict]:
            return redoc, 200, {"content-type": "text/html"}

        self.route("/redoc")(redoc_handler)
