from collections.abc import Callable
from inspect import Parameter
from typing import Annotated, Any, NewType, TypeAlias, TypeVar

from attrs import frozen, has
from cattrs import Converter
from cattrs._compat import get_args, is_annotated

from .responses import ResponseException
from .status import BadRequest, BaseResponse

try:
    from orjson import loads
except ImportError:
    from json import loads

from . import Cookie

T = TypeVar("T")
RequestLoaderPredicate: TypeAlias = Callable[[Parameter], bool]


@frozen
class JsonBodyLoader:
    """Metadata for customized loading and structuring of JSON bodies."""

    content_type: str | None = "application/json"
    error_handler: Callable[
        [Exception, bytes], BaseResponse
    ] = lambda _, __: BadRequest("invalid payload")


@frozen
class HeaderSpec:
    """Metadata for loading headers."""

    name: str | Callable[[str], str] = lambda n: n.replace("_", "-")


ReqBody = Annotated[T, JsonBodyLoader()]
ReqBytes = NewType("ReqBytes", bytes)

#: A header dependency.
Header: TypeAlias = Annotated[T, HeaderSpec()]


def get_cookie_name(t, arg_name: str) -> str | None:
    if t is Cookie or t is Cookie | None:
        return arg_name

    if is_annotated(t):
        for arg in get_args(t)[1:]:
            if arg.__class__ is Cookie:
                return arg or arg_name
    return None


def maybe_header_type(p: Parameter) -> tuple[type, HeaderSpec] | None:
    """Get the Annotated HeaderSpec, if present."""
    t = p.annotation
    if is_annotated(t):
        args = get_args(t)
        if args:
            for arg in args[1:]:
                if isinstance(arg, HeaderSpec):
                    return args[0], arg
    return None


def get_header_type(p: Parameter) -> tuple[type, HeaderSpec]:
    """Similar to `maybe_req_body_attrs`, except raises."""
    res = maybe_header_type(p)
    if res is None:
        # Shouldn't happen.
        raise Exception("No header info found")
    return res


def is_header(p: Parameter) -> bool:
    return maybe_header_type(p) is not None


def attrs_body_factory(
    parameter: Parameter, converter: Converter
) -> Callable[[ReqBytes], Any]:
    attrs_cls, loader = get_req_body_attrs(parameter)

    def structure_body(body: ReqBytes) -> Any:
        try:
            return converter.structure(loads(body), attrs_cls)
        except Exception as exc:
            raise ResponseException(loader.error_handler(exc, body)) from exc

    return structure_body


def maybe_req_body_type(p: Parameter) -> tuple[type, JsonBodyLoader] | None:
    """Is this parameter a valid request body?"""
    t = p.annotation
    if is_annotated(t):
        args = get_args(t)
        if args and (has(args[0]) or getattr(args[0], "__origin__", None) is dict):
            for arg in args[1:]:
                if isinstance(arg, JsonBodyLoader):
                    return args[0], arg
    return None


def get_req_body_attrs(p: Parameter) -> tuple[type, JsonBodyLoader]:
    """Similar to `maybe_req_body_attrs`, except raises."""
    res = maybe_req_body_type(p)
    if res is None:
        raise Exception("No attrs request body found")
    return res


def is_req_body_attrs(p: Parameter) -> bool:
    return maybe_req_body_type(p) is not None
