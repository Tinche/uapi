from typing import Callable, Optional, TypeAlias, TypeVar

R = TypeVar("R")
CB = Callable[..., R]

Routes: TypeAlias = dict[tuple[str, str], tuple[Callable, Optional[str]]]
PathParamParser: TypeAlias = Callable[[str], tuple[str, list[str]]]


def is_subclass(cls, subclass) -> bool:
    """A more robust version."""
    try:
        return issubclass(cls, subclass)
    except TypeError:
        return False
