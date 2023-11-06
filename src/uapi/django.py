from collections.abc import Callable
from functools import partial
from inspect import Parameter, Signature, signature
from typing import Any, ClassVar, TypeAlias, TypeVar

from attrs import Factory, define
from cattrs import Converter
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest as FrameworkRequest
from django.http import HttpResponse as FrameworkResponse
from django.urls import URLPattern
from django.urls import path as django_path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
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
from .responses import dict_to_headers, make_exception_adapter, make_return_adapter
from .status import BaseResponse, get_status_code
from .types import Method, RouteName, RouteTags

__all__ = ["App"]

C = TypeVar("C")


def make_django_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Starlette."""
    res = Incanter()

    def query_factory(p: Parameter):
        def read_query(_request: FrameworkRequest) -> Any:
            return converter.structure(
                _request.GET[p.name]
                if p.default is Signature.empty
                else _request.GET.get(p.name, p.default),
                p.annotation,
            )

        return read_query

    res.register_hook_factory(
        lambda p: p.annotation is not FrameworkRequest, query_factory
    )

    def string_query_factory(p: Parameter):
        def read_query(_request: FrameworkRequest) -> str:
            return (
                _request.GET[p.name]
                if p.default is Signature.empty
                else _request.GET.get(p.name, p.default)
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

    def request_bytes(_request: FrameworkRequest) -> bytes:
        return _request.body

    res.register_hook(lambda p: p.annotation is ReqBytes, request_bytes)
    res.register_hook_factory(
        is_req_body_attrs, partial(attrs_body_factory, converter=converter)
    )

    # RouteNames and methods get an empty hook, so the parameter propagates to the base incanter.
    res.hook_factory_registry.insert(
        0, Hook(lambda p: p.annotation in (RouteName, Method), None)
    )

    return res


def _make_method_router(
    methods_to_handlers: dict[Method, Callable]
) -> Callable[[FrameworkRequest], FrameworkResponse]:
    def method_router(request: FrameworkRequest) -> FrameworkResponse:
        if request.method in methods_to_handlers:
            return methods_to_handlers[request.method](request)

        return FrameworkResponse(status=405)

    return method_router


@define
class DjangoApp(BaseApp):
    framework_incant: Incanter = Factory(
        lambda self: make_django_incanter(self.converter), takes_self=True
    )
    _framework_req_cls: ClassVar[type] = FrameworkRequest
    _framework_resp_cls: ClassVar[type] = FrameworkResponse

    @staticmethod
    def _path_param_parser(p: str) -> tuple[str, list[str]]:
        return (strip_path_param_prefix(angle_to_curly(p)), parse_curly_path_params(p))

    def to_urlpatterns(self) -> list[URLPattern]:
        res = []

        by_path_by_method: dict[
            str, dict[Method, tuple[Callable, RouteName, RouteTags]]
        ] = {}
        for (method, path), v in self._route_map.items():
            by_path_by_method.setdefault(path, {})[method] = v

        exc_adapter = make_exception_adapter(self.converter)

        for path, methods_and_handlers in by_path_by_method.items():
            # Django does not strip the prefix slash, so we do it for it.
            path = path.removeprefix("/")
            per_method_adapted = {}
            for method, (handler, name, _) in methods_and_handlers.items():
                ra = make_return_adapter(
                    signature(handler, eval_str=True).return_annotation,
                    FrameworkResponse,
                    self.converter,
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

                    def adapted(
                        request: WSGIRequest,
                        _fra=_framework_return_adapter,
                        _ea=exc_adapter,
                        _handler=adapted,
                        _path_params=path_params,
                        _path_types=path_types,
                        _req_ct=req_ct,
                        _rn=name,
                        _rm=method,
                        **kwargs: Any,
                    ) -> FrameworkResponse:
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", status=415
                            )
                        path_args = {
                            p: (
                                self.converter.structure(kwargs[p], path_type)
                                if (path_type := _path_types[p])
                                not in (str, Signature.empty)
                                else kwargs[p]
                            )
                            for p in _path_params
                        }
                        try:
                            return _handler(request, _rn, _rm, **path_args)
                        except ResponseException as exc:
                            return _fra(_ea(exc))

                else:

                    def adapted(
                        request: WSGIRequest,
                        _ra=ra,
                        _fra=_framework_return_adapter,
                        _ea=exc_adapter,
                        _handler=adapted,
                        _path_params=path_params,
                        _path_types=path_types,
                        _req_ct=req_ct,
                        _rn=name,
                        _rm=method,
                        **kwargs: Any,
                    ) -> FrameworkResponse:
                        if (
                            _req_ct is not None
                            and request.headers.get("content-type") != _req_ct
                        ):
                            return FrameworkResponse(
                                f"invalid content type (expected {_req_ct})", status=415
                            )
                        path_args = {
                            p: (
                                self.converter.structure(kwargs[p], path_type)
                                if (path_type := _path_types[p])
                                not in (str, Signature.empty)
                                else kwargs[p]
                            )
                            for p in _path_params
                        }
                        try:
                            return _fra(_ra(_handler(request, _rn, _rm, **path_args)))
                        except ResponseException as exc:
                            return _fra(_ea(exc))

                per_method_adapted[method] = adapted

            if len(methods_and_handlers) > 1:
                # Django cannot easily do different handlers on the same path,
                # so we do this ourselves.
                router = _make_method_router(per_method_adapted)
                res.append(
                    django_path(
                        path,
                        require_http_methods(list(methods_and_handlers))(
                            csrf_exempt(router)
                        ),
                        name=next(iter(methods_and_handlers.values()))[1],
                    )
                )
            else:
                res.append(
                    django_path(
                        path,
                        require_http_methods(method)(csrf_exempt(adapted)),
                        name=name,
                    )
                )

        return res


App: TypeAlias = DjangoApp


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
            return _request.COOKIES[cookie_name]

        return read_cookie

    def read_cookie_opt(_request: FrameworkRequest) -> Any:
        return _request.COOKIES.get(cookie_name, default)

    return read_cookie_opt


def _framework_return_adapter(resp: BaseResponse) -> FrameworkResponse:
    if resp.headers:
        return FrameworkResponse(
            resp.ret or b"",
            status=get_status_code(resp.__class__),  # type: ignore
            headers=dict_to_headers(resp.headers),
        )

    return FrameworkResponse(
        resp.ret or b"", status=get_status_code(resp.__class__)  # type: ignore
    )
