from typing import Callable, TypeVar

CB = TypeVar("CB", bound=Callable)


def is_subclass(cls, subclass) -> bool:
    """A more robust version."""
    try:
        return issubclass(cls, subclass)
    except TypeError:
        return False
