from inspect import Signature, signature
from typing import Awaitable, Callable, Final, TypeVar

from attrs import Factory, define, has
from cattrs import Converter
from incant import Hook, Incanter
from quart import Quart
from quart import Response as FrameworkResponse
from quart import request
from werkzeug.datastructures import Headers

try:
    from orjson import loads
except ImportError:
    from json import loads  # type: ignore

from . import App, ResponseException
from .path import (
    angle_to_curly,
    parse_angle_path_params,
    parse_curly_path_params,
    strip_path_param_prefix,
)
from .requests import get_cookie_name
from .responses import dict_to_headers, identity, make_return_adapter
from .status import BadRequest, BaseResponse, get_status_code

C = TypeVar("C")


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

    def attrs_body_factory(attrs_cls: type[C]) -> Callable[[], Awaitable[C]]:
        async def structure_body() -> C:
            if not request.is_json:
                raise ResponseException(BadRequest("invalid content-type"))
            return converter.structure(loads(await request.data), attrs_cls)

        return structure_body

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
    res.register_hook_factory(
        lambda p: has(p.annotation), lambda p: attrs_body_factory(p.annotation)
    )
    return res


def framework_return_adapter(resp: BaseResponse):
    return FrameworkResponse(
        resp.ret or b"",
        get_status_code(resp.__class__),  # type: ignore
        Headers(dict_to_headers(resp.headers)) if resp.headers else None,
    )


@define
class QuartApp(App):
    framework_incant: Incanter = Factory(
        lambda self: make_quart_incanter(self.converter), takes_self=True
    )
    _path_param_parser: Callable[[str], tuple[str, list[str]]] = lambda p: (
        strip_path_param_prefix(angle_to_curly(p)),
        parse_curly_path_params(p),
    )
    _framework_resp_cls = FrameworkResponse

    def to_framework_app(self, import_name: str) -> Quart:
        q = Quart(import_name)

        for (method, path), (handler, name) in self.route_map.items():
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse, self.converter
            )
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            if ra is None:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )

                def outer(prepared=prepared):
                    async def adapted(**kwargs):
                        return await prepared(**kwargs)

                    return adapted

                adapted = outer()

            else:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )

                if ra == identity:

                    def outer(prepared=prepared, _fra=framework_return_adapter):
                        async def adapted(**kwargs):
                            try:
                                return _fra(await prepared(**kwargs))
                            except ResponseException as exc:
                                return _fra(exc.response)

                        return adapted

                    adapted = outer()

                else:

                    def outer(prepared=prepared, _fra=framework_return_adapter, _ra=ra):
                        async def adapted(**kwargs):  # type: ignore
                            try:
                                return _fra(_ra(await prepared(**kwargs)))
                            except ResponseException as exc:
                                return _fra(exc.response)

                        return adapted

                    adapted = outer()

            q.route(
                path,
                methods=[method],
                endpoint=name if name is not None else handler.__name__,
            )(adapted)

        return q

    async def run(self, port: int = 8000):
        from uvicorn import Config, Server  # type: ignore

        config = Config(self.to_framework_app(__name__), port=port, access_log=False)
        server = Server(config=config)
        await server.serve()


App: Final = QuartApp
