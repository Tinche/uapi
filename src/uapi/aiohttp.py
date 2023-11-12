from asyncio import sleep
from collections.abc import Callable
from functools import partial
from inspect import Parameter, Signature, signature
from logging import Logger
from typing import Any, ClassVar, TypeAlias, TypeVar

from aiohttp.web import AppRunner
from aiohttp.web import Request as FrameworkRequest
from aiohttp.web import Response, RouteTableDef
from aiohttp.web import StreamResponse as FrameworkResponse
from aiohttp.web import TCPSite, access_logger
from aiohttp.web_app import Application
from attrs import Factory, define
from cattrs import Converter
from incant import Hook, Incanter
from multidict import CIMultiDict

from . import ResponseException
from .base import App as BaseApp
from .path import parse_curly_path_params
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

__all__ = ["App", "AiohttpApp"]

C = TypeVar("C")


def make_aiohttp_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Aiohttp."""
    res = Incanter()

    def query_factory(p: Parameter):
        def read_query(_request: FrameworkRequest):
            return converter.structure(
                _request.query[p.name]
                if p.default is Signature.empty
                else _request.query.get(p.name, p.default),
                p.annotation,
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation is not FrameworkRequest, query_factory
    )

    def string_query_factory(p: Parameter) -> Callable[[FrameworkRequest], Any]:
        def read_query(_request: FrameworkRequest):
            return (
                _request.query[p.name]
                if p.default is Signature.empty
                else _request.query.get(p.name, p.default)
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation in (Signature.empty, str), string_query_factory
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

    # RouteNames and methods get an empty hook, so the parameter propagates to the base incanter.
    res.hook_factory_registry.insert(
        0, Hook(lambda p: p.annotation in (RouteName, Method), None)
    )

    return res


@define
class AiohttpApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_aiohttp_incanter(self.converter), takes_self=True
    )
    _framework_req_cls: ClassVar[type] = FrameworkRequest
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    @staticmethod
    def _path_param_parser(p: str) -> tuple[str, list[str]]:
        return (p, parse_curly_path_params(p))

    def __attrs_post_init__(self) -> None:
        async def request_bytes(_request: FrameworkRequest) -> bytes:
            return await _request.read()

        self.framework_incant.register_hook(
            lambda p: p.annotation is ReqBytes, request_bytes
        )

        self.framework_incant.register_hook_factory(
            is_req_body_attrs, partial(attrs_body_factory, converter=self.converter)
        )

    def to_framework_routes(self) -> RouteTableDef:
        r = RouteTableDef()
        exc_adapter = make_exception_adapter(self.converter)

        for (method, path), (handler, name, _) in self._route_map.items():
            ra = make_return_adapter(
                signature(handler, eval_str=True).return_annotation,
                FrameworkResponse,
                self.converter,
            )
            path_params = parse_curly_path_params(path)
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
            sig = signature(prepared)
            path_types = {p: sig.parameters[p].annotation for p in path_params}

            adapted = self.framework_incant.adapt(
                prepared,
                lambda p: p.annotation is FrameworkRequest,
                lambda p: p.annotation is RouteName,
                lambda p: p.annotation is Method,
                **{pp: (lambda p, _pp=pp: p.name == _pp) for pp in path_params},
            )

            if ra is None:

                async def adapted(
                    request: FrameworkRequest,
                    _fra=_framework_return_adapter,
                    _ea=exc_adapter,
                    _prepared=adapted,
                    _path_params=path_params,
                    _path_types=path_types,
                    _req_ct=req_ct,
                    _rn=name,
                    _rm=method,
                ) -> FrameworkResponse:
                    if (
                        _req_ct is not None
                        and request.headers.get("content-type") != _req_ct
                    ):
                        return Response(
                            body=f"invalid content type (expected {_req_ct})",
                            status=415,
                        )

                    path_args = {
                        p: (
                            self.converter.structure(request.match_info[p], path_type)
                            if (path_type := _path_types[p])
                            not in (str, Signature.empty)
                            else request.match_info[p]
                        )
                        for p in _path_params
                    }
                    try:
                        return await _prepared(request, _rn, _rm, **path_args)
                    except ResponseException as exc:
                        return _fra(_ea(exc))

            else:

                async def adapted(
                    request: FrameworkRequest,
                    _ra=ra,
                    _fra=_framework_return_adapter,
                    _ea=exc_adapter,
                    _handler=adapted,
                    _path_params=path_params,
                    _path_types=path_types,
                    _req_ct=req_ct,
                    _rn=name,
                    _rm=method,
                ) -> FrameworkResponse:
                    if (
                        _req_ct is not None
                        and request.headers.get("content-type") != _req_ct
                    ):
                        return Response(
                            body=f"invalid content type (expected {_req_ct})",
                            status=415,
                        )
                    path_args = {
                        p: (
                            self.converter.structure(request.match_info[p], path_type)
                            if (path_type := _path_types[p])
                            not in (str, Signature.empty)
                            else request.match_info[p]
                        )
                        for p in _path_params
                    }
                    try:
                        return _fra(_ra(await _handler(request, _rn, _rm, **path_args)))
                    except ResponseException as exc:
                        return _fra(_ea(exc))

            r.route(method, path, name=name)(adapted)

        return r

    async def run(
        self,
        port: int = 8000,
        host: str | None = None,
        handle_signals: bool = True,
        shutdown_timeout: float = 60,
        access_log: Logger | None = access_logger,
        handler_cancellation: bool = False,
    ):
        """Start serving this app.

        If `handle_signals` is `False`, cancel the task running this to shut down.

        :param handle_signals: Whether to let the underlying server handle signals.
        """
        app = Application()
        app.add_routes(self.to_framework_routes())
        runner = AppRunner(
            app,
            handle_signals=handle_signals,
            access_log=access_log,
            handler_cancellation=handler_cancellation,
        )
        await runner.setup()
        site = TCPSite(runner, host, port, shutdown_timeout=shutdown_timeout)
        await site.start()

        while True:
            await sleep(3600)


App: TypeAlias = AiohttpApp


def make_header_dependency(
    type: type,
    headerspec: HeaderSpec,
    name: str,
    converter: Converter,
    default: Any = Signature.empty,
) -> Callable[[FrameworkRequest], Any]:
    if isinstance(headerspec.name, str):
        name = headerspec.name
    else:
        name = headerspec.name(name)

    if type is str:
        if default is Signature.empty:

            def read_header(_request: FrameworkRequest) -> str:
                return _request.headers[name]

            return read_header

        def read_opt_header(_request: FrameworkRequest) -> Any:
            return _request.headers.get(name, default)

        return read_opt_header

    handler = converter._structure_func.dispatch(type)
    if default is Signature.empty:

        def read_conv_header(_request: FrameworkRequest) -> str:
            return handler(_request.headers[name], type)

        return read_conv_header

    def read_opt_conv_header(_request: FrameworkRequest) -> Any:
        return handler(_request.headers.get(name, default), type)

    return read_opt_conv_header


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie(_request: FrameworkRequest) -> str:
            return _request.cookies[cookie_name]

        return read_cookie

    def read_opt_cookie(_request: FrameworkRequest) -> Any:
        return _request.cookies.get(cookie_name, default)

    return read_opt_cookie


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    return Response(
        body=resp.ret or b"",
        status=get_status_code(resp.__class__),  # type: ignore
        headers=CIMultiDict(dict_to_headers(resp.headers)) if resp.headers else None,
    )
