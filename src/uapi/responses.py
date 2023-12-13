from collections.abc import Callable, Iterable, Mapping
from inspect import Signature
from types import MappingProxyType, NoneType
from typing import Any, TypeVar, get_args

from attrs import has
from cattrs import Converter
from cattrs._compat import is_union_type
from incant import is_subclass
from orjson import dumps

from .shorthands import ResponseShorthand, can_shorthand_handle
from .status import BaseResponse, Headers, Ok, ResponseException

empty_dict: Mapping[str, str] = MappingProxyType({})


def make_response_adapter(
    return_type: Any,
    framework_response_cls: type,
    converter: Converter,
    shorthands: Iterable[type[ResponseShorthand]],
) -> Callable[[Any], BaseResponse] | None:
    """Potentially create a function to adapt the return type to
    something uapi understands.
    """
    # breakpoint()
    if return_type is Signature.empty or is_subclass(
        return_type, framework_response_cls
    ):
        # You're on your own, buddy.
        return None

    for shorthand in shorthands:
        can_handle = can_shorthand_handle(return_type, shorthand)
        if can_handle:
            return shorthand.response_adapter

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

    if is_union_type(return_type):
        return _make_union_response_adapter(
            get_args(return_type), converter, shorthands
        )
    return identity


def _make_union_response_adapter(
    types: tuple[Any],
    converter: Converter,
    shorthands: Iterable[type[ResponseShorthand]],
) -> Callable[[Any], BaseResponse] | None:
    # First, we check if any shorthands match.
    shorthand_checks = []
    for member in types:
        for shorthand in shorthands:
            if can_shorthand_handle(member, shorthand):
                shorthand_checks.append(shorthand)
                break

    if not shorthand_checks:
        # No shorthands, it's all BaseResponses.
        return lambda val: val.__class__(
            ret=dumps(converter.unstructure(val.ret)),
            headers=val.headers | {"content-type": "application/json"},
        )

    def response_adapter(val: Any, _shs=shorthand_checks) -> BaseResponse:
        for sh in _shs:
            if sh.is_union_member(val):
                return sh.response_adapter(val)
        return val.__class__(
            ret=dumps(converter.unstructure(val.ret)),
            headers=val.headers | {"content-type": "application/json"},
        )

    return response_adapter


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


T = TypeVar("T")


def identity(x: T) -> T:
    """The identity function, used and recognized for certain optimizations."""
    return x


def dict_to_headers(d: Headers) -> list[tuple[str, str]]:
    return [(k, v) if k[:9] != "__cookie_" else ("set-cookie", v) for k, v in d.items()]
