from collections.abc import Callable
from functools import partial
from inspect import Parameter, Signature, signature
from typing import Any, ClassVar, Generic, TypeAlias, TypeVar

from attrs import Factory, define
from cattrs import Converter
from incant import Hook, Incanter

from flask import Flask, request
from flask import Response as FrameworkResponse

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
    get_form_type,
    get_header_type,
    get_req_body_attrs,
    is_form,
    is_header,
    is_req_body_attrs,
)
from .responses import dict_to_headers, make_exception_adapter, make_response_adapter
from .status import BadRequest, BaseResponse, get_status_code
from .types import Method, RouteName

__all__ = ["App", "FlaskApp"]

C = TypeVar("C")
C_contra = TypeVar("C_contra", contravariant=True)


@define
class FlaskApp(Generic[C_contra], BaseApp[C_contra | FrameworkResponse]):
    framework_incant: Incanter = Factory(
        lambda self: _make_flask_incanter(self.converter), takes_self=True
    )
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    def to_framework_app(self, import_name: str) -> Flask:
        f = Flask(import_name)
        exc_adapter = make_exception_adapter(self.converter)

        for (method, path), (handler, name, _) in self._route_map.items():
            ra = make_response_adapter(
                signature(handler, eval_str=True).return_annotation,
                FrameworkResponse,
                self.converter,
                self._shorthands,
            )
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            base_handler = self.incant.compose(handler, is_async=False)
            # Detect required content-types here, based on the registered
            # request loaders.
            base_sig = signature(base_handler)
            req_ct: str | None = None
            for arg in base_sig.parameters.values():
                if is_req_body_attrs(arg):
                    _, loader = get_req_body_attrs(arg)
                    req_ct = loader.content_type

            prepared = self.framework_incant.compose(
                base_handler, hooks, is_async=False
            )
            adapted = self.framework_incant.adapt(
                prepared,
                lambda p: p.annotation is RouteName,
                lambda p: p.annotation is Method,
                **{pp: (lambda p, _pp=pp: p.name == _pp) for pp in path_params},
            )
            if ra is None:

                def o0(
                    _handler=adapted,
                    _req_ct=req_ct,
                    _fra=_framework_return_adapter,
                    _ea=exc_adapter,
                    _rn=name,
                    _rm=method,
                ):
                    def adapter(**kwargs):
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", 415
                            )
                        try:
                            return _handler(_rn, _rm, **kwargs)
                        except ResponseException as exc:
                            return _fra(_ea(exc))

                    return adapter

                adapted = o0()

            else:

                def o1(
                    _handler=adapted,
                    _ra=ra,
                    _fra=_framework_return_adapter,
                    _req_ct=req_ct,
                    _ea=exc_adapter,
                    _rn=name,
                    _rm=method,
                ):
                    def adapter(**kwargs):
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", 415
                            )
                        try:
                            return _fra(_ra(_handler(_rn, _rm, **kwargs)))
                        except ResponseException as exc:
                            return _fra(_ea(exc))

                    return adapter

                adapted = o1()

            f.route(
                path,
                methods=[method],
                endpoint=name if name is not None else handler.__name__,
            )(adapted)

        return f

    def run(self, import_name: str, host: str | None = None, port: int = 8000):
        """Start serving the app using the Flask development server."""
        self.to_framework_app(import_name).run(host=host, port=port)

    @staticmethod
    def _path_param_parser(p: str) -> tuple[str, list[str]]:
        return (strip_path_param_prefix(angle_to_curly(p)), parse_curly_path_params(p))


App: TypeAlias = FlaskApp[FrameworkResponse]


def _make_flask_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Flask."""
    res = Incanter()

    res.register_hook_factory(
        lambda _: True,
        lambda p: lambda: converter.structure(
            (
                request.args[p.name]
                if p.default is Signature.empty
                else request.args.get(p.name, p.default)
            ),
            p.annotation,
        ),
    )
    res.register_hook_factory(
        lambda p: p.annotation in (Signature.empty, str),
        lambda p: lambda: (
            request.args[p.name]
            if p.default is Signature.empty
            else request.args.get(p.name, p.default)
        ),
    )

    def string_list_query_factory(p: Parameter) -> Callable[[], list[str]]:
        def read_query() -> list[str]:
            return (
                request.args.getlist(p.name)
                if p.default is Signature.empty
                else (
                    request.args.getlist(p.name)
                    if p.name in request.args
                    else p.default
                )
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation == list[str], string_list_query_factory
    )

    def nonstring_list_query_factory(p: Parameter) -> Callable[[], list]:
        def read_query():
            return (
                converter.structure(request.args.getlist(p.name), p.annotation)
                if p.default is Signature.empty
                else (
                    converter.structure(request.args.getlist(p.name), p.annotation)
                    if p.name in request.args
                    else p.default
                )
            )

        return read_query

    res.register_hook_factory(
        lambda p: getattr(p.annotation, "__origin__", None) is list,
        nonstring_list_query_factory,
    )

    res.register_hook_factory(
        is_header,
        lambda p: _make_header_dependency(
            *get_header_type(p), p.name, converter, p.default
        ),
    )
    res.register_hook_factory(
        lambda p: get_cookie_name(p.annotation, p.name) is not None,
        lambda p: _make_cookie_dependency(get_cookie_name(p.annotation, p.name), default=p.default),  # type: ignore
    )

    def request_bytes() -> bytes:
        return request.data

    res.register_hook(lambda p: p.annotation is ReqBytes, request_bytes)

    res.register_hook_factory(
        is_req_body_attrs, partial(attrs_body_factory, converter=converter)
    )

    res.register_hook_factory(
        is_form, lambda p: _make_form_dependency(get_form_type(p), converter)
    )

    # RouteNames and methods get an empty hook, so the parameter propagates to the base incanter.
    res.hook_factory_registry.insert(
        0, Hook(lambda p: p.annotation in (RouteName, Method), None)
    )

    return res


def _make_header_dependency(
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

    handler = converter.get_structure_hook(type)

    if default is Signature.empty:

        def read_conv_header() -> str:
            return handler(request.headers[name], type)

        return read_conv_header

    def read_opt_conv_header() -> Any:
        return handler(request.headers.get(name, default), type)

    return read_opt_conv_header


def _make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie() -> str:
            return request.cookies[cookie_name]

        return read_cookie

    def read_cookie_opt() -> Any:
        return request.cookies.get(cookie_name, default)

    return read_cookie_opt


def _make_form_dependency(type: type[C], converter: Converter) -> Callable[[], C]:
    handler = converter.get_structure_hook(type)

    def read_form() -> C:
        try:
            return handler(request.form, type)
        except Exception as exc:
            raise ResponseException(BadRequest("invalid payload")) from exc

    return read_form


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    return FrameworkResponse(
        resp.ret or b"", get_status_code(resp.__class__), dict_to_headers(resp.headers)  # type: ignore
    )
