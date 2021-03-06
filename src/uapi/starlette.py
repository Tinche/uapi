from inspect import Parameter, Signature, signature
from typing import Awaitable, Callable, ClassVar, TypeVar

from attrs import Factory, define, has
from cattrs import Converter
from incant import Hook, Incanter
from starlette.applications import Starlette
from starlette.requests import Request as FrameworkRequest
from starlette.responses import Response as FrameworkResponse

try:
    from orjson import loads
except ImportError:
    from json import loads

from . import App as BaseApp
from . import ResponseException
from .path import parse_curly_path_params
from .requests import get_cookie_name
from .responses import identity, make_return_adapter
from .status import BadRequest, BaseResponse, Headers, get_status_code

C = TypeVar("C")


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie(request: FrameworkRequest):
            return request.cookies[cookie_name]

    else:

        def read_cookie(request: FrameworkRequest):
            return request.cookies.get(cookie_name, default)

    return read_cookie


def extract_cookies(headers: Headers) -> tuple[dict[str, str], list[str]]:
    h = {}
    cookies = []
    for k, v in headers.items():
        if k[:9] == "__cookie_":
            cookies.append(v)
        else:
            h[k] = v
    return h, cookies


def make_starlette_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Starlette."""
    res = Incanter()

    def attrs_body_factory(
        attrs_cls: type[C],
    ) -> Callable[[FrameworkRequest], Awaitable[C]]:
        async def structure_body(request: FrameworkRequest) -> C:
            if request.headers["content-type"] != "application/json":
                raise ResponseException(BadRequest("invalid content-type"))
            return converter.structure(loads(await request.body()), attrs_cls)

        return structure_body

    def query_factory(p: Parameter):
        def read_query(request: FrameworkRequest):
            return converter.structure(
                request.query_params[p.name]
                if p.default is Signature.empty
                else request.query_params.get(p.name, p.default),
                p.annotation,
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation is not FrameworkRequest, query_factory
    )

    def string_query_factory(p: Parameter):
        def read_query(request: FrameworkRequest):
            return (
                request.query_params[p.name]
                if p.default is Signature.empty
                else request.query_params.get(p.name, p.default)
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
        lambda p: has(p.annotation), lambda p: attrs_body_factory(p.annotation)
    )
    return res


def framework_return_adapter(resp: BaseResponse):
    if resp.headers:
        headers, cookies = extract_cookies(resp.headers)
        res = FrameworkResponse(
            resp.ret or b"", get_status_code(resp.__class__), headers  # type: ignore
        )
        for cookie in cookies:
            res.raw_headers.append((b"set-cookie", cookie.encode("latin1")))
        return res
    else:
        return FrameworkResponse(resp.ret or b"", get_status_code(resp.__class__))  # type: ignore


@define
class StarletteApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_starlette_incanter(self.converter), takes_self=True
    )
    _path_param_parser: Callable[[str], tuple[str, list[str]]] = lambda p: (
        p,
        parse_curly_path_params(p),
    )
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    def to_framework_app(self) -> Starlette:
        s = Starlette()

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
                            self.converter.structure(request.path_params[p], path_type)
                            if (path_type := _path_types[p])
                            not in (str, Signature.empty)
                            else request.path_params[p]
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
                        _fra=framework_return_adapter,
                        _prepared=prepared,
                        _path_params=path_params,
                        _path_types=path_types,
                    ) -> FrameworkResponse:
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
                        _fra=framework_return_adapter,
                        _prepared=prepared,
                        _path_params=path_params,
                        _path_types=path_types,
                    ) -> FrameworkResponse:
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

            s.add_route(path, adapted, name=name, methods=[method])

        return s

    async def run(self, port: int = 8000):
        from uvicorn import Config, Server  # type: ignore

        config = Config(self.to_framework_app(), port=port, access_log=False)
        server = Server(config=config)
        await server.serve()


App = StarletteApp
