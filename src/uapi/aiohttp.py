from inspect import Parameter, Signature, signature
from typing import Callable, ClassVar, TypeVar

from aiohttp.web import Request as FrameworkRequest
from aiohttp.web import Response as FrameworkResponse
from aiohttp.web import RouteTableDef, _run_app
from aiohttp.web_app import Application
from attrs import Factory, define
from cattrs import Converter
from incant import Hook, Incanter
from multidict import CIMultiDict

try:
    from orjson import loads
except ImportError:
    from json import loads

from . import ResponseException
from .base import App as BaseApp
from .path import parse_curly_path_params
from .requests import get_cookie_name, get_req_body_attrs, is_req_body_attrs
from .responses import dict_to_headers, identity, make_return_adapter
from .status import BadRequest, BaseResponse, get_status_code

C = TypeVar("C")


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie(request: FrameworkRequest):
            return request.cookies[cookie_name]

    else:

        def read_cookie(request: FrameworkRequest):
            return request.cookies.get(cookie_name, default)

    return read_cookie


def make_aiohttp_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Aiohttp."""
    res = Incanter()

    def query_factory(p: Parameter):
        def read_query(request: FrameworkRequest):
            return converter.structure(
                request.query[p.name]
                if p.default is Signature.empty
                else request.query.get(p.name, p.default),
                p.annotation,
            )

        return read_query

    def attrs_body_factory(attrs_cls: type[C]):
        async def structure_body(request: FrameworkRequest) -> C:
            if request.headers.get("content-type") != "application/json":
                raise ResponseException(BadRequest("invalid content-type"))
            return converter.structure(await request.json(loads=loads), attrs_cls)

        return structure_body

    res.register_hook_factory(
        lambda p: p.annotation is not FrameworkRequest, query_factory
    )

    def string_query_factory(p: Parameter):
        def read_query(request: FrameworkRequest):
            return (
                request.query[p.name]
                if p.default is Signature.empty
                else request.query.get(p.name, p.default)
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation in (Signature.empty, str), string_query_factory
    )
    res.register_hook_factory(
        lambda p: get_cookie_name(p.annotation, p.name) is not None,
        lambda p: make_cookie_dependency(get_cookie_name(p.annotation, p.name), default=p.default),  # type: ignore
    )
    res.register_hook_factory(
        is_req_body_attrs, lambda p: attrs_body_factory(get_req_body_attrs(p))
    )
    return res


def _framework_return_adapter(resp: BaseResponse):
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

    def to_framework_routes(self) -> RouteTableDef:
        r = RouteTableDef()

        for (method, path), (handler, name) in self.route_map.items():
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse, self.converter
            )
            path_params = parse_curly_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]
            if ra is None:
                base_handler = self.base_incant.prepare(handler, is_async=True)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=True
                )
                sig = signature(prepared)
                path_types = {p: sig.parameters[p].annotation for p in path_params}

                async def adapted(
                    request: FrameworkRequest,
                    _incant=self.framework_incant.aincant,
                    _prepared=prepared,
                    _path_params=path_params,
                    _path_types=path_types,
                ) -> FrameworkResponse:
                    path_args = {
                        p: (
                            self.converter.structure(request.match_info[p], path_type)
                            if (path_type := _path_types[p])
                            not in (str, Signature.empty)
                            else request.match_info[p]
                        )
                        for p in _path_params
                    }
                    return await _incant(_prepared, request=request, **path_args)

            else:
                base_handler = self.base_incant.prepare(handler, is_async=True)
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
                    ) -> FrameworkResponse:
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.match_info[p], path_type
                                )
                                if (path_type := path_types[p])
                                not in (str, Signature.empty)
                                else request.match_info[p]
                            )
                            for p in path_params
                        }
                        try:
                            return _fra(
                                await _incant(_prepared, request=request, **path_args)
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
                    ) -> FrameworkResponse:
                        path_args = {
                            p: (
                                self.converter.structure(
                                    request.match_info[p], path_type
                                )
                                if (path_type := path_types[p])
                                not in (str, Signature.empty)
                                else request.match_info[p]
                            )
                            for p in path_params
                        }
                        try:
                            return _fra(
                                _ra(
                                    await _incant(
                                        _prepared, request=request, **path_args
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
