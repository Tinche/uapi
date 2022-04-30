from inspect import Signature, signature
from typing import Callable, Final

from attrs import Factory, define, has
from cattrs import Converter
from flask import Flask
from flask import Response as FrameworkResponse
from flask import request
from incant import Hook, Incanter

try:
    from orjson import loads
except ImportError:
    from json import loads  # type: ignore

from . import App, ResponseException
from .path import (
    angle_to_curly,
    parse_angle_path_params,
    parse_curly_path_params,
    strip_path_param_prefix,
)
from .requests import get_cookie_name
from .responses import dict_to_headers, identity, make_return_adapter
from .status import BadRequest, BaseResponse, get_status_code


def make_cookie_dependency(cookie_name: str, default=Signature.empty):
    if default is Signature.empty:

        def read_cookie():
            return request.cookies[cookie_name]

    else:

        def read_cookie():
            return request.cookies.get(cookie_name, default)

    return read_cookie


def make_flask_incanter(converter: Converter) -> Incanter:
    """Create the framework incanter for Quart."""
    res = Incanter()

    def attrs_body_factory(attrs_cls: type):
        def structure_body() -> attrs_cls:  # type: ignore
            if not request.is_json:
                raise ResponseException(BadRequest("invalid content-type"))
            return converter.structure(loads(request.data), attrs_cls)

        return structure_body

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
    res.register_hook_factory(
        lambda p: has(p.annotation), lambda p: attrs_body_factory(p.annotation)
    )
    return res


def framework_return_adapter(resp: BaseResponse):
    return FrameworkResponse(
        resp.ret or b"", get_status_code(resp.__class__), dict_to_headers(resp.headers)  # type: ignore
    )


@define
class FlaskApp(App):
    framework_incant: Incanter = Factory(
        lambda self: make_flask_incanter(self.converter), takes_self=True
    )
    _path_param_parser: Callable[[str], tuple[str, list[str]]] = lambda p: (
        strip_path_param_prefix(angle_to_curly(p)),
        parse_curly_path_params(p),
    )
    _framework_resp_cls = FrameworkResponse

    def to_framework_app(self, import_name: str) -> Flask:
        f = Flask(import_name)

        for (method, path), (handler, name) in self.route_map.items():
            ra = make_return_adapter(
                signature(handler).return_annotation, FrameworkResponse, self.converter
            )
            path_params = parse_angle_path_params(path)
            hooks = [Hook.for_name(p, None) for p in path_params]

            if ra is None:
                base_handler = self.base_incant.prepare(handler, is_async=False)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=False
                )

                def outer(prepared=prepared):
                    def adapted(**kwargs):
                        return prepared(**kwargs)

                    return adapted

                adapted = outer()

            else:
                base_handler = self.base_incant.prepare(handler, is_async=False)
                prepared = self.framework_incant.prepare(
                    base_handler, hooks, is_async=False
                )
                if ra == identity:

                    def outer(prepared=prepared):
                        def adapted(**kwargs):
                            try:
                                return framework_return_adapter(prepared(**kwargs))
                            except ResponseException as exc:
                                return framework_return_adapter(exc.response)

                        return adapted

                    adapted = outer()

                else:

                    def outer(prepared=prepared, ra=ra):
                        def adapted(**kwargs):
                            try:
                                return framework_return_adapter(ra(prepared(**kwargs)))
                            except ResponseException as exc:
                                return framework_return_adapter(exc.response)

                        return adapted

                    adapted = outer()

            f.route(
                path,
                methods=[method],
                endpoint=name if name is not None else handler.__name__,
            )(adapted)

        return f

    def run(self, port: int = 8000):
        self.flask.run(port=port)


App: Final = FlaskApp
