from asyncio import create_task, sleep
from collections.abc import Callable
from contextlib import suppress
from functools import partial
from inspect import Parameter, Signature, signature
from typing import Any, ClassVar, TypeAlias, TypeVar

from attrs import Factory, define
from cattrs import Converter
from incant import Hook, Incanter
from starlette.applications import Starlette
from starlette.requests import Request as FrameworkRequest
from starlette.responses import Response as FrameworkResponse

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
from .responses import make_exception_adapter, make_return_adapter
from .status import BaseResponse, Headers, get_status_code
from .types import Method, RouteName

__all__ = ["App"]

C = TypeVar("C")


def make_starlette_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Starlette."""
    res = Incanter()

    def query_factory(p: Parameter) -> Callable[[FrameworkRequest], Any]:
        def read_query(_request: FrameworkRequest) -> Any:
            return converter.structure(
                _request.query_params[p.name]
                if p.default is Signature.empty
                else _request.query_params.get(p.name, p.default),
                p.annotation,
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation is not FrameworkRequest, query_factory
    )

    def string_query_factory(p: Parameter) -> Callable[[FrameworkRequest], Any]:
        def read_query(_request: FrameworkRequest) -> Any:
            return (
                _request.query_params[p.name]
                if p.default is Signature.empty
                else _request.query_params.get(p.name, p.default)
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

    async def request_bytes(_request: FrameworkRequest) -> bytes:
        return await _request.body()

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
class StarletteApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_starlette_incanter(self.converter), takes_self=True
    )
    _framework_req_cls: ClassVar[type] = FrameworkRequest
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    @staticmethod
    def _path_param_parser(p: str) -> tuple[str, list[str]]:
        return (p, parse_curly_path_params(p))

    def to_framework_app(self) -> Starlette:
        s = Starlette()
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
                        return FrameworkResponse(
                            f"invalid content type (expected {_req_ct})", 415
                        )
                    try:
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.path_params[p], path_type
                                )
                                if (path_type := _path_types[p])
                                not in (str, Signature.empty)
                                else request.path_params[p]
                            )
                            for p in _path_params
                        }
                        return await _handler(request, _rn, _rm, **path_args)
                    except ResponseException as exc:
                        return _fra(_ea(exc))

            else:

                async def adapted(
                    request: FrameworkRequest,
                    _ra=ra,
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
                        return FrameworkResponse(
                            f"invalid content type (expected {_req_ct})", 415
                        )
                    path_args = {
                        p: (
                            self.converter.structure(request.path_params[p], path_type)
                            if (path_type := _path_types[p])
                            not in (str, Signature.empty)
                            else request.path_params[p]
                        )
                        for p in _path_params
                    }
                    try:
                        return _fra(
                            _ra(await _prepared(request, _rn, _rm, **path_args))
                        )
                    except ResponseException as exc:
                        return _fra(_ea(exc))

            s.add_route(path, adapted, name=name, methods=[method])

        return s

    async def run(
        self,
        port: int = 8000,
        handle_signals: bool = True,
        log_level: str | int | None = None,
    ) -> None:
        """Start serving this app using uvicorn.

        Cancel the task running this to shut down uvicorn.
        """
        from uvicorn import Config, Server

        config = Config(
            self.to_framework_app(), port=port, access_log=False, log_level=log_level
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


App: TypeAlias = StarletteApp


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

    def read_cookie_opt(_request: FrameworkRequest) -> Any:
        return _request.cookies.get(cookie_name, default)

    return read_cookie_opt


def extract_cookies(headers: Headers) -> tuple[dict[str, str], list[str]]:
    h = {}
    cookies = []
    for k, v in headers.items():
        if k[:9] == "__cookie_":
            cookies.append(v)
        else:
            h[k] = v
    return h, cookies


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    if resp.headers:
        headers, cookies = extract_cookies(resp.headers)
        res = FrameworkResponse(
            resp.ret or b"", get_status_code(resp.__class__), headers  # type: ignore
        )
        for cookie in cookies:
            res.raw_headers.append((b"set-cookie", cookie.encode("latin1")))
        return res
    return FrameworkResponse(resp.ret or b"", get_status_code(resp.__class__))  # type: ignore
