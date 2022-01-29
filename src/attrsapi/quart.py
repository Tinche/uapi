from inspect import Signature, signature
from typing import Any, Callable, Tuple, Union, cast

from attrs import Factory, define
from cattrs import Converter
from flask.app import Flask
from incant import Hook, Incanter
from quart import Quart
from quart import Response as FrameworkResponse
from quart import request

from . import BaseApp
from .flask import make_openapi_spec as flask_openapi_spec
from .path import parse_angle_path_params
from .requests import get_cookie_name
from .responses import make_return_adapter

try:
    from functools import partial

    from ujson import dumps as usjon_dumps

    dumps: Callable[[Any], Union[bytes, str]] = partial(
        usjon_dumps, ensure_ascii=False, escape_forward_slashes=False
    )
except ImportError:
    from json import dumps


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie():
            return request.cookies[cookie_name]

    else:

        def read_cookie():
            return request.cookies.get(cookie_name, default)

    return read_cookie


def make_quart_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Quart."""
    res = Incanter()
    res.register_hook_factory(
        lambda _: True,
        lambda p: lambda: converter.structure(
            request.args[p.name]
            if p.default is Signature.empty
            else request.args.get(p.name, p.default),
            p.annotation,
        ),
    )
    res.register_hook_factory(
        lambda p: p.annotation in (Signature.empty, str),
        lambda p: lambda: request.args[p.name]
        if p.default is Signature.empty
        else request.args.get(p.name, p.default),
    )
    res.register_hook_factory(
        lambda p: get_cookie_name(p.annotation, p.name) is not None,
        lambda p: make_cookie_dependency(get_cookie_name(p.annotation, p.name), default=p.default),  # type: ignore
    )
    return res


def framework_return_adapter(val: Tuple[Any, int, dict]):
    return FrameworkResponse(val[0] or b"", val[1], val[2])


@define
class App(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_quart_incanter(self.converter), takes_self=True
    )

    def route(self, path: str, app: Quart, methods=["GET"]):
        def wrapper(handler: Callable) -> Callable:
            ra = make_return_adapter(signature(handler).return_annotation)
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            if ra is None:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )

                async def adapted(**kwargs):
                    return await prepared(**kwargs)

            else:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )

                async def adapted(**kwargs):
                    return framework_return_adapter(ra(await prepared(**kwargs)))

            adapted.__attrsapi_handler__ = base_handler  # type: ignore

            app.route(path, methods=methods, endpoint=handler.__name__)(adapted)
            return adapted

        return wrapper


def make_openapi_spec(app: Quart, title: str = "Server", version: str = "1.0"):
    return flask_openapi_spec(
        cast(Flask, app), title, version, native_response_cl=FrameworkResponse
    )
