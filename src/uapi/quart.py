from functools import partial
from inspect import Signature, signature
from typing import Any, Callable, ClassVar, TypeVar

from attrs import Factory, define
from cattrs import Converter
from incant import Hook, Incanter
from quart import Quart
from quart import Response as FrameworkResponse
from quart import request
from werkzeug.datastructures import Headers

from . import ResponseException
from .base import App as BaseApp
from .path import (
    angle_to_curly,
    parse_angle_path_params,
    parse_curly_path_params,
    strip_path_param_prefix,
)
from .requests import (
    ReqBytes,
    attrs_body_factory,
    get_cookie_name,
    get_req_body_attrs,
    is_req_body_attrs,
)
from .responses import dict_to_headers, identity, make_return_adapter
from .status import BaseResponse, get_status_code

C = TypeVar("C")


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie() -> str:
            return request.cookies[cookie_name]

        return read_cookie

    else:

        def read_cookie_opt() -> Any:
            return request.cookies.get(cookie_name, default)

        return read_cookie_opt


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

    async def request_bytes() -> bytes:
        return await request.data

    res.register_hook(lambda p: p.annotation is ReqBytes, request_bytes)

    res.register_hook_factory(
        is_req_body_attrs, partial(attrs_body_factory, converter=converter)
    )
    return res


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    return FrameworkResponse(
        resp.ret or b"",
        get_status_code(resp.__class__),  # type: ignore
        Headers(dict_to_headers(resp.headers)) if resp.headers else None,
    )


@define
class QuartApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_quart_incanter(self.converter), takes_self=True
    )
    _path_param_parser: Callable[[str], tuple[str, list[str]]] = lambda p: (
        strip_path_param_prefix(angle_to_curly(p)),
        parse_curly_path_params(p),
    )
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    def to_framework_app(self, import_name: str) -> Quart:
        q = Quart(import_name)

        for (method, path), (handler, name) in self.route_map.items():
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse, self.converter
            )
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            base_handler = self.base_incant.prepare(handler, is_async=True)
            # Detect required content-types here, based on the registered
            # request loaders.
            base_sig = signature(base_handler)
            req_ct: str | None = None
            for arg in base_sig.parameters.values():
                if is_req_body_attrs(arg):
                    _, loader = get_req_body_attrs(arg)
                    req_ct = loader.content_type

            if ra is None:
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )

                def o0(
                    prepared=prepared, _req_ct=req_ct, _fra=_framework_return_adapter
                ):
                    async def adapted(**kwargs):
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", 415
                            )
                        try:
                            return await prepared(**kwargs)
                        except ResponseException as exc:
                            return _fra(exc.response)

                    return adapted

                adapted = o0()

            else:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )

                if ra == identity:

                    def o1(
                        prepared=prepared,
                        _fra=_framework_return_adapter,
                        _req_ct=req_ct,
                    ):
                        async def adapted(**kwargs):
                            if (
                                _req_ct is not None
                                and request.headers.get("content-type") != _req_ct
                            ):
                                return FrameworkResponse(
                                    f"invalid content type (expected {_req_ct})", 415
                                )
                            try:
                                return _fra(await prepared(**kwargs))
                            except ResponseException as exc:
                                return _fra(exc.response)

                        return adapted

                    adapted = o1()

                else:

                    def o2(
                        prepared=prepared,
                        _fra=_framework_return_adapter,
                        _ra=ra,
                        _req_ct=req_ct,
                    ):
                        async def adapted(**kwargs):
                            if (
                                _req_ct is not None
                                and request.headers.get("content-type") != _req_ct
                            ):
                                return FrameworkResponse(
                                    f"invalid content type (expected {_req_ct})", 415
                                )
                            try:
                                return _fra(_ra(await prepared(**kwargs)))
                            except ResponseException as exc:
                                return _fra(exc.response)

                        return adapted

                    adapted = o2()

            q.route(
                path,
                methods=[method],
                endpoint=name if name is not None else handler.__name__,
            )(adapted)

        return q

    async def run(self, import_name: str, port: int = 8000):
        from uvicorn import Config, Server

        config = Config(self.to_framework_app(import_name), port=port, access_log=False)
        server = Server(config=config)
        await server.serve()


App = QuartApp
