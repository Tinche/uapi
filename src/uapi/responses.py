from inspect import Signature
from types import MappingProxyType
from typing import Any, Callable, Mapping, Optional, get_args

from attrs import has
from cattrs import Converter
from cattrs._compat import is_union_type
from incant import is_subclass

from .status import BaseResponse, Headers, Ok, get_status_code

try:
    from orjson import dumps as dumps
except ImportError:
    from json import dumps as dumps  # type: ignore

__all__ = ["dumps", "return_type_to_statuses", "get_status_code_results"]
empty_dict: Mapping[str, str] = MappingProxyType({})


def make_return_adapter(
    return_type: Any, framework_response_cls: type, converter: Converter
) -> Optional[Callable[..., BaseResponse]]:
    if return_type in (Signature.empty, framework_response_cls):
        # You're on your own, buddy.
        return None
    if return_type is None:
        return lambda r: Ok(None)
    if return_type in (str, bytes):
        return lambda r: Ok(r)
    if has(return_type):
        return lambda r: Ok(
            dumps(converter.unstructure(r, unstructure_as=return_type)),
            {"content-type": "application/json"},
        )
    if is_subclass(getattr(return_type, "__origin__", None), BaseResponse) and has(
        inner := return_type.__args__[0]
    ):
        return lambda r: return_type(
            dumps(converter.unstructure(r.ret, unstructure_as=inner)),
            r.headers | {"content-type": "application/json"},
        )
    return identity


def return_type_to_statuses(t: type) -> dict[int, Any]:
    per_status: dict[int, Any] = {}
    for t in get_args(t) if is_union_type(t) else [t]:
        if is_subclass(t, BaseResponse) or is_subclass(
            getattr(t, "__origin__", None), BaseResponse
        ):
            status = get_status_code(t.__origin__)  # type: ignore
            t = t.__args__[0]  # type: ignore
        else:
            status = 200
        if status in per_status:
            per_status[status] = per_status[status] | t
        else:
            per_status[status] = t
    return per_status


def get_status_code_results(t: type) -> list[tuple[int, Any]]:
    """Normalize a supported return type into (status code, type)."""
    return list(return_type_to_statuses(t).items())


def identity(*args):
    """The identity function, used and recognized for certain optimizations."""
    return args


def dict_to_headers(d: Headers) -> list[tuple[str, str]]:
    return [
        (k, v) if not k[:9] == "__cookie_" else ("set-cookie", v) for k, v in d.items()
    ]
