from collections.abc import Callable, Mapping
from inspect import Signature
from types import MappingProxyType, NoneType
from typing import Any, TypeVar, get_args

from attrs import define, has
from cattrs import Converter
from cattrs._compat import is_union_type
from incant import is_subclass

from .status import BaseResponse, Headers, NoContent, Ok, get_status_code

try:
    from orjson import dumps
except ImportError:
    from json import dumps  # type: ignore

__all__ = ["dumps", "return_type_to_statuses", "get_status_code_results"]

empty_dict: Mapping[str, str] = MappingProxyType({})


@define
class ResponseException(Exception):
    """An exception that is converted into an HTTP response."""

    response: BaseResponse


def no_content(_, _nc: NoContent = NoContent()) -> NoContent:
    return _nc


def make_return_adapter(
    return_type: Any, framework_response_cls: type, converter: Converter
) -> Callable[..., BaseResponse] | None:
    if return_type is Signature.empty or is_subclass(
        return_type, framework_response_cls
    ):
        # You're on your own, buddy.
        return None
    if return_type is None:
        return no_content
    if return_type is bytes:
        return lambda r: Ok(r, {"content-type": "application/octet-stream"})
    if return_type is str:
        return lambda r: Ok(r, {"content-type": "text/plain"})
    if is_subclass(return_type, BaseResponse):
        return identity
    if is_subclass(getattr(return_type, "__origin__", None), BaseResponse) and has(
        inner := return_type.__args__[0]
    ):
        return lambda r: return_type(
            dumps(converter.unstructure(r.ret, unstructure_as=inner)),
            r.headers | {"content-type": "application/json"},
        )
    # attrs classes (but not ours)
    if has(return_type) and not is_subclass(
        getattr(return_type, "__origin__", None), BaseResponse
    ):
        return lambda r: Ok(
            dumps(converter.unstructure(r, unstructure_as=return_type)),
            {"content-type": "application/json"},
        )
    if is_union_type(return_type) and all(
        is_subclass(getattr(a, "__origin__", a), BaseResponse)
        and (a is NoContent or has(get_args(a)[0]) or get_args(a)[0] is NoneType)
        for a in get_args(return_type)
    ):
        return lambda r: r.__class__(
            ret=dumps(converter.unstructure(r.ret)) if r.ret is not None else None,
            headers=r.headers | {"content-type": "application/json"},
        )
    return identity


def make_exception_adapter(
    converter: Converter,
) -> Callable[[ResponseException], BaseResponse]:
    """Produce an adapter of exceptions to BaseResponses.

    Since exception types aren't statically known, this can be
    simpler than the return adapter.
    """

    def adapt_exception(exc: ResponseException) -> BaseResponse:
        if isinstance(exc.response.ret, str | bytes | None):
            return exc.response
        return exc.response.__class__(
            dumps(converter.unstructure(exc.response.ret)),
            {"content-type": "application/json"} | exc.response.headers,
        )

    return adapt_exception


def return_type_to_statuses(t: type) -> dict[int, Any]:
    per_status: dict[int, Any] = {}
    for typ in get_args(t) if is_union_type(t) else [t]:
        if is_subclass(typ, BaseResponse) or is_subclass(
            getattr(typ, "__origin__", None), BaseResponse
        ):
            if hasattr(typ, "__origin__"):
                status = get_status_code(typ.__origin__)
                typ = typ.__args__[0]
            else:
                status = get_status_code(typ)
                typ = type(None)
        elif typ in (None, NoneType):
            status = 204
        else:
            status = 200
        if status in per_status:
            per_status[status] = per_status[status] | typ
        else:
            per_status[status] = typ
    return per_status


def get_status_code_results(t: type) -> list[tuple[int, Any]]:
    """Normalize a supported return type into (status code, type)."""
    return list(return_type_to_statuses(t).items())


T = TypeVar("T")


def identity(x: T) -> T:
    """The identity function, used and recognized for certain optimizations."""
    return x


def dict_to_headers(d: Headers) -> list[tuple[str, str]]:
    return [(k, v) if k[:9] != "__cookie_" else ("set-cookie", v) for k, v in d.items()]
