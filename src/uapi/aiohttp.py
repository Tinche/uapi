from functools import partial
from inspect import Parameter, Signature, signature
from typing import Any, Callable, ClassVar, TypeVar

from aiohttp.web import Request as FrameworkRequest
from aiohttp.web import Response as FrameworkResponse
from aiohttp.web import RouteTableDef, _run_app
from aiohttp.web_app import Application
from attrs import Factory, define
from cattrs import Converter
from incant import Hook, Incanter
from multidict import CIMultiDict

from . import ResponseException
from .base import App as BaseApp
from .path import parse_curly_path_params
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

        def read_cookie(_request: FrameworkRequest) -> str:
            return _request.cookies[cookie_name]

        return read_cookie

    else:

        def read_opt_cookie(_request: FrameworkRequest) -> Any:
            return _request.cookies.get(cookie_name, default)

        return read_opt_cookie


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
        lambda p: get_cookie_name(p.annotation, p.name) is not None,
        lambda p: make_cookie_dependency(get_cookie_name(p.annotation, p.name), default=p.default),  # type: ignore
    )
    return res


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    return FrameworkResponse(
        body=resp.ret or b"",
        status=get_status_code(resp.__class__),  # type: ignore
        headers=CIMultiDict(dict_to_headers(resp.headers)) if resp.headers else None,
    )


@define
class AiohttpApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_aiohttp_incanter(self.converter), takes_self=True
    )
    _path_param_parser: Callable[[str], tuple[str, list[str]]] = lambda p: (
        p,
        parse_curly_path_params(p),
    )
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

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

        for (method, path), (handler, name) in self.route_map.items():
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse, self.converter
            )
            path_params = parse_curly_path_params(path)
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
                sig = signature(prepared)
                path_types = {p: sig.parameters[p].annotation for p in path_params}

                async def adapted(
                    request: FrameworkRequest,
                    _incant=self.framework_incant.aincant,
                    _fra=_framework_return_adapter,
                    _prepared=prepared,
                    _path_params=path_params,
                    _path_types=path_types,
                    _req_ct=req_ct,
                ) -> FrameworkResponse:
                    if (
                        _req_ct is not None
                        and request.headers.get("content-type") != _req_ct
                    ):
                        return FrameworkResponse(
                            body=f"invalid content type (expected {_req_ct})",
                            status=415,
                        )

                    try:
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.match_info[p], path_type
                                )
                                if (path_type := _path_types[p])
                                not in (str, Signature.empty)
                                else request.match_info[p]
                            )
                            for p in _path_params
                        }
                        return await _incant(_prepared, _request=request, **path_args)
                    except ResponseException as exc:
                        return _fra(exc.response)

            else:
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )
                sig = signature(prepared)
                path_types = {p: sig.parameters[p].annotation for p in path_params}

                if ra == identity:

                    async def adapted(  # type: ignore
                        request: FrameworkRequest,
                        _incant=self.framework_incant.aincant,
                        _fra=_framework_return_adapter,
                        _prepared=prepared,
                        _path_params=path_params,
                        _req_ct=req_ct,
                    ) -> FrameworkResponse:
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                body=f"invalid content type (expected {_req_ct})",
                                status=415,
                            )
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.match_info[p], path_type
                                )
                                if (path_type := path_types[p])
                                not in (str, Signature.empty)
                                else request.match_info[p]
                            )
                            for p in _path_params
                        }
                        try:
                            return _fra(
                                await _incant(_prepared, _request=request, **path_args)
                            )
                        except ResponseException as exc:
                            return _fra(exc.response)

                else:

                    async def adapted(  # type: ignore
                        request: FrameworkRequest,
                        _incant=self.framework_incant.aincant,
                        _ra=ra,
                        _fra=_framework_return_adapter,
                        _prepared=prepared,
                        _path_params=path_params,
                        _path_types=path_types,
                        _req_ct=req_ct,
                    ) -> FrameworkResponse:
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                body=f"invalid content type (expected {_req_ct})",
                                status=415,
                            )
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.match_info[p], path_type
                                )
                                if (path_type := _path_types[p])
                                not in (str, Signature.empty)
                                else request.match_info[p]
                            )
                            for p in _path_params
                        }
                        try:
                            return _fra(
                                _ra(
                                    await _incant(
                                        _prepared, _request=request, **path_args
                                    )
                                )
                            )
                        except ResponseException as exc:
                            return _fra(exc.response)

            r.route(method, path, name=name)(adapted)

        return r

    async def run(self, port: int = 8000):
        app = Application()
        app.add_routes(self.to_framework_routes())

        await _run_app(app, port=port)


App = AiohttpApp
