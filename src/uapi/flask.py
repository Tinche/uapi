from functools import partial
from inspect import Signature, signature
from typing import Any, ClassVar

from attrs import Factory, define
from cattrs import Converter
from flask import Flask
from flask import Response as FrameworkResponse
from flask import request
from incant import Hook, Incanter

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
from .responses import dict_to_headers, identity, make_return_adapter
from .status import BaseResponse, get_status_code
from .types import PathParamParser


def make_flask_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Flask."""
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

    def request_bytes() -> bytes:
        return request.data

    res.register_hook(lambda p: p.annotation is ReqBytes, request_bytes)

    res.register_hook_factory(
        is_req_body_attrs, partial(attrs_body_factory, converter=converter)
    )
    return res


@define
class FlaskApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_flask_incanter(self.converter), takes_self=True
    )
    _path_param_parser: ClassVar[PathParamParser] = lambda p: (
        strip_path_param_prefix(angle_to_curly(p)),
        parse_curly_path_params(p),
    )
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    def to_framework_app(self, import_name: str) -> Flask:
        f = Flask(import_name)

        for (method, path), (handler, name, _) in self._route_map.items():
            ra = make_return_adapter(
                signature(handler, eval_str=True).return_annotation,
                FrameworkResponse,
                self.converter,
            )
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            base_handler = self.incant.prepare(handler, is_async=False)
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
                    base_handler, hooks, is_async=False
                )

                def o0(
                    prepared=prepared, _req_ct=req_ct, _fra=_framework_return_adapter
                ):
                    def adapted(**kwargs):
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", 415
                            )
                        try:
                            return prepared(**kwargs)
                        except ResponseException as exc:
                            return _fra(exc.response)

                    return adapted

                adapted = o0()

            else:
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=False
                )
                if ra == identity:

                    def o1(prepared=prepared, _req_ct=req_ct):
                        def adapted(**kwargs):
                            if (
                                _req_ct is not None
                                and request.headers.get("content-type") != _req_ct
                            ):
                                return FrameworkResponse(
                                    f"invalid content type (expected {_req_ct})", 415
                                )
                            try:
                                return _framework_return_adapter(prepared(**kwargs))
                            except ResponseException as exc:
                                return _framework_return_adapter(exc.response)

                        return adapted

                    adapted = o1()

                else:

                    def o2(prepared=prepared, ra=ra, _req_ct=req_ct):
                        def adapted(**kwargs):
                            if (
                                _req_ct is not None
                                and request.headers.get("content-type") != _req_ct
                            ):
                                return FrameworkResponse(
                                    f"invalid content type (expected {_req_ct})", 415
                                )
                            try:
                                return _framework_return_adapter(ra(prepared(**kwargs)))
                            except ResponseException as exc:
                                return _framework_return_adapter(exc.response)

                        return adapted

                    adapted = o2()

            f.route(
                path,
                methods=[method],
                endpoint=name if name is not None else handler.__name__,
            )(adapted)

        return f

    def run(self, import_name: str, port: int = 8000):
        self.to_framework_app(import_name).run(port=port)


App = FlaskApp


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

        else:

            def read_opt_header() -> Any:
                return request.headers.get(name, default)

            return read_opt_header
    else:
        handler = converter._structure_func.dispatch(type)
        if default is Signature.empty:

            def read_header() -> str:
                return handler(request.headers[name], type)

            return read_header

        else:

            def read_opt_header() -> Any:
                return handler(request.headers.get(name, default), type)

            return read_opt_header


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie() -> str:
            return request.cookies[cookie_name]

        return read_cookie

    else:

        def read_cookie_opt() -> Any:
            return request.cookies.get(cookie_name, default)

        return read_cookie_opt


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    return FrameworkResponse(
        resp.ret or b"", get_status_code(resp.__class__), dict_to_headers(resp.headers)  # type: ignore
    )
