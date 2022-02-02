from inspect import Signature, signature
from json import dumps
from typing import Any, Callable, Literal, Optional, Tuple, cast

from attrs import Factory, define
from cattrs import Converter
from flask.app import Flask
from incant import Hook, Incanter
from quart import Quart
from quart import Response as FrameworkResponse
from quart import request
from werkzeug.datastructures import Headers

from . import BaseApp
from .flask import make_openapi_spec as flask_openapi_spec
from .openapi import converter as openapi_converter
from .path import parse_angle_path_params
from .requests import get_cookie_name
from .responses import dict_to_headers, identity, make_return_adapter


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


def framework_return_adapter(val: Tuple[Any, int, dict[str, str]]):
    return FrameworkResponse(
        val[0] or b"", val[1], Headers(dict_to_headers(val[2])) if val[2] else None
    )


@define
class App(BaseApp):
    quart: Quart = Factory(lambda: Quart(__name__))
    framework_incant: Incanter = Factory(
        lambda self: make_quart_incanter(self.converter), takes_self=True
    )

    def get(self, path, name: Optional[str] = None, quart: Optional[Quart] = None):
        return self.route(path, name, quart)

    def post(self, path, name: Optional[str] = None, quart: Optional[Quart] = None):
        return self.route(path, name=name, quart=quart, methods=["POST"])

    def patch(self, path, name: Optional[str] = None, quart: Optional[Quart] = None):
        return self.route(path, name=name, quart=quart, methods=["PATCH"])

    def delete(self, path, name: Optional[str] = None, quart: Optional[Quart] = None):
        return self.route(path, name, quart, methods=["DELETE"])

    def route(
        self,
        path: str,
        name: Optional[str] = None,
        quart: Optional[Quart] = None,
        methods=["GET"],
    ):
        q = quart or self.quart

        def wrapper(handler: Callable) -> Callable:
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse
            )
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

                if ra == identity:

                    async def adapted(_fra=framework_return_adapter, **kwargs):
                        return _fra(await prepared(**kwargs))

                else:

                    async def adapted(_fra=framework_return_adapter, _ra=ra, **kwargs):
                        return _fra(_ra(await prepared(**kwargs)))

            adapted.__attrsapi_handler__ = base_handler  # type: ignore

            q.route(
                path,
                methods=methods,
                endpoint=name if name is not None else handler.__name__,
            )(adapted)
            return adapted

        return wrapper

    def serve_openapi(self, path: str = "/openapi.json", quart: Optional[Quart] = None):
        openapi = make_openapi_spec(quart or self.quart)
        payload = openapi_converter.unstructure(openapi)

        async def openapi_handler() -> tuple[str, Literal[200], dict]:
            return dumps(payload), 200, {"content-type": "application/json"}

        self.route(path)(openapi_handler)

    async def run(self, port: int = 8000):
        from uvicorn import Config, Server

        config = Config(self.quart, port=port, access_log=False)
        server = Server(config=config)
        await server.serve()


def make_openapi_spec(app: Quart, title: str = "Server", version: str = "1.0"):
    return flask_openapi_spec(
        cast(Flask, app), title, version, native_response_cl=FrameworkResponse
    )
