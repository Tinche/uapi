from asyncio import create_task, sleep
from contextlib import suppress
from functools import partial
from inspect import Signature, signature
from typing import Any, ClassVar, TypeAlias, TypeVar

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
    HeaderSpec,
    ReqBytes,
    attrs_body_factory,
    get_cookie_name,
    get_header_type,
    get_req_body_attrs,
    is_header,
    is_req_body_attrs,
)
from .responses import dict_to_headers, make_exception_adapter, make_return_adapter
from .status import BaseResponse, get_status_code
from .types import Method, RouteName

__all__ = ["App"]

C = TypeVar("C")


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
        is_header,
        lambda p: make_header_dependency(
            *get_header_type(p), p.name, converter, p.default
        ),
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

    # RouteNames and methods get an empty hook, so the parameter propagates to the base incanter.
    res.hook_factory_registry.insert(
        0, Hook(lambda p: p.annotation in (RouteName, Method), None)
    )

    return res


@define
class QuartApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_quart_incanter(self.converter), takes_self=True
    )
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    @staticmethod
    def _path_param_parser(p: str) -> tuple[str, list[str]]:
        return (strip_path_param_prefix(angle_to_curly(p)), parse_curly_path_params(p))

    def to_framework_app(self, import_name: str) -> Quart:
        q = Quart(import_name)
        exc_adapter = make_exception_adapter(self.converter)

        for (method, path), (handler, name, _) in self._route_map.items():
            ra = make_return_adapter(
                signature(handler, eval_str=True).return_annotation,
                FrameworkResponse,
                self.converter,
            )
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            base_handler = self.incant.compose(handler, is_async=True)
            # Detect required content-types here, based on the registered
            # request loaders.
            base_sig = signature(base_handler)
            req_ct: str | None = None
            for arg in base_sig.parameters.values():
                if is_req_body_attrs(arg):
                    _, loader = get_req_body_attrs(arg)
                    req_ct = loader.content_type
            prepared = self.framework_incant.compose(base_handler, hooks, is_async=True)
            adapted = self.framework_incant.adapt(
                prepared,
                lambda p: p.annotation is RouteName,
                lambda p: p.annotation is Method,
                **{pp: (lambda p, _pp=pp: p.name == _pp) for pp in path_params},
            )

            if ra is None:

                def o0(
                    handler=adapted,
                    _req_ct=req_ct,
                    _fra=_framework_return_adapter,
                    _ea=exc_adapter,
                    _rn=name,
                    _rm=method,
                ):
                    async def adapter(**kwargs):
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", 415
                            )
                        try:
                            return await handler(_rn, _rm, **kwargs)
                        except ResponseException as exc:
                            return _fra(_ea(exc))

                    return adapter

                adapted = o0()

            else:

                def o1(
                    handler=adapted,
                    _fra=_framework_return_adapter,
                    _ra=ra,
                    _req_ct=req_ct,
                    _ea=exc_adapter,
                    _rn=name,
                    _rm=method,
                ):
                    async def adapter(**kwargs):
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", 415
                            )
                        try:
                            return _fra(_ra(await handler(_rn, _rm, **kwargs)))
                        except ResponseException as exc:
                            return _fra(_ea(exc))

                    return adapter

                adapted = o1()

            q.route(
                path,
                methods=[method],
                endpoint=name if name is not None else handler.__name__,
            )(adapted)

        return q

    async def run(
        self,
        import_name: str,
        port: int = 8000,
        handle_signals: bool = True,
        log_level: str | int | None = None,
    ) -> None:
        """Start serving this app using uvicorn.

        Cancel the task running this to shut down uvicorn.
        """
        from uvicorn import Config, Server

        config = Config(
            self.to_framework_app(import_name),
            port=port,
            access_log=False,
            log_level=log_level,
        )

        if handle_signals:
            server = Server(config=config)
            await server.serve()
        else:

            class NoSignalsServer(Server):
                def install_signal_handlers(self) -> None:
                    return

            server = NoSignalsServer(config=config)

            t = create_task(server.serve())

            with suppress(BaseException):
                while True:
                    await sleep(360)
            server.should_exit = True
            await t


App: TypeAlias = QuartApp


def make_header_dependency(
    type: type,
    headerspec: HeaderSpec,
    name: str,
    converter: Converter,
    default: Any = Signature.empty,
):
    if isinstance(headerspec.name, str):
        name = headerspec.name
    else:
        name = headerspec.name(name)
    if type is str:
        if default is Signature.empty:

            def read_header() -> str:
                return request.headers[name]

            return read_header

        def read_opt_header() -> Any:
            return request.headers.get(name, default)

        return read_opt_header

    handler = converter._structure_func.dispatch(type)
    if default is Signature.empty:

        def read_conv_header() -> str:
            return handler(request.headers[name], type)

        return read_conv_header

    def read_opt_conv_header() -> Any:
        return handler(request.headers.get(name, default), type)

    return read_opt_conv_header


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie() -> str:
            return request.cookies[cookie_name]

        return read_cookie

    def read_cookie_opt() -> Any:
        return request.cookies.get(cookie_name, default)

    return read_cookie_opt


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    return FrameworkResponse(
        resp.ret or b"",
        get_status_code(resp.__class__),  # type: ignore
        Headers(dict_to_headers(resp.headers)) if resp.headers else None,
    )
