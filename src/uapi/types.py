from typing import Callable, TypeVar

R = TypeVar("R")
CB = Callable[..., R]


def is_subclass(cls, subclass) -> bool:
    """A more robust version."""
    try:
        return issubclass(cls, subclass)
    except TypeError:
        return False
