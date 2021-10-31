from typing import Any, get_args, get_origin

from cattr._compat import is_literal


def returns_status_code(t: type) -> bool:
    return (
        get_origin(t) is tuple
        and is_literal(first_arg := (get_args(t)[0]))
        and type(get_args(first_arg)[0]) == int
    )


def get_status_code_results(t: type) -> list[tuple[int, Any]]:
    if not returns_status_code(t):
        return [(200, t)]
    args = get_args(t)
    return [(get_args(args[0])[0], args[1])]  # type: ignore
