from typing import Any, Callable, Union, get_args, get_origin

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


def returns_status_code(t: type) -> bool:
    return all(
        (
            get_origin(t) is tuple
            and is_literal(first_arg := (get_args(t)[0]))
            and type(get_args(first_arg)[0]) == int
        )
        for t in (get_args(t) if is_union_type(t) else [t])
    )


def get_status_code_results(t: type) -> list[tuple[int, Any]]:
    if not returns_status_code(t):
        return [(200, t)]
    resp_types = get_args(t) if is_union_type(t) else (t,)
    return [(get_args(get_args(t)[0])[0], get_args(t)[1]) for t in resp_types]  # type: ignore
