"""Internal shorthands stuff."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from incant import is_subclass

if TYPE_CHECKING:
    from .shorthands import ResponseShorthand


def get_shorthand_type(shorthand: type[ResponseShorthand]) -> Any:
    """Get the underlying shorthand type (ResponseShorthand[T] -> T)."""
    return shorthand.__orig_bases__[0].__args__[0]  # type: ignore


def can_shorthand_handle(type: Any, shorthand: type[ResponseShorthand]) -> bool:
    res = shorthand.can_handle(type)
    return res is True or (
        res == "check_type"
        and ((st := get_shorthand_type(shorthand)) is type or is_subclass(type, st))
    )
