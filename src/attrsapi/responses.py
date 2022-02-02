from inspect import Signature
from typing import Any, Callable, Dict, Optional, Tuple, Union, get_args, get_origin

from cattr._compat import is_literal, is_union_type

try:
    from functools import partial

    from ujson import dumps as usjon_dumps

    dumps: Callable[[Any], Union[bytes, str]] = partial(
        usjon_dumps, ensure_ascii=False, escape_forward_slashes=False
    )
except ImportError:
    from json import dumps as dumps

__all__ = ["dumps", "returns_status_code", "get_status_code_results"]
empty_dict: Dict[str, str] = {}


def make_return_adapter(
    return_type: Any, framework_response_cls: type
) -> Optional[Callable[..., Tuple]]:
    if return_type in (Signature.empty, framework_response_cls):
        # You're on your own, buddy.
        return None
    if return_type is None:
        return lambda r: (None, 200, empty_dict)
    if return_type in (str, bytes):
        return lambda r: (r, 200, empty_dict)
    if get_origin(return_type) is tuple:
        if len(get_args(return_type)) == 2:
            return lambda r: (r[0], r[1], empty_dict)
        if len(get_args(return_type)) == 3:
            return identity
    if is_union_type(return_type):
        return (
            lambda r: r
            if len(r) == 3
            else ((r[0], r[1], empty_dict) if len(r) == 2 else (r[0], 200, empty_dict))
        )
    return None


def returns_status_code(t: type) -> bool:
    return all(
        (
            get_origin(t) is tuple
            and is_literal(second_arg := (get_args(t)[1]))
            and type(get_args(second_arg)[0]) == int
        )
        for t in (get_args(t) if is_union_type(t) else [t])
    )


def get_status_code_results(t: type) -> list[tuple[int, Any]]:
    """Normalize a supported return type into (status code, type)."""
    if not returns_status_code(t):
        return [(200, t)]
    resp_types = get_args(t) if is_union_type(t) else (t,)
    return [(get_args((get_args(t)[1]))[0], get_args(t)[0]) for t in resp_types]  # type: ignore


def identity(*args):
    """The identity function, used and recognized for certain optimizations."""
    return args


def dict_to_headers(d: dict[str, str]) -> list[tuple[str, str]]:
    return [
        (k, v) if not k[:9] == "__cookie_" else ("set-cookie", v) for k, v in d.items()
    ]
