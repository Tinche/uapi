from typing import Callable, Final, Optional, TypeVar

R = TypeVar("R")
CB = Callable[..., R]

Routes: Final = dict[tuple[str, str], tuple[Callable, Optional[str]]]
PathParamParser: Final = Callable[[str], tuple[str, list[str]]]


def is_subclass(cls, subclass) -> bool:
    """A more robust version."""
    try:
        return issubclass(cls, subclass)
    except TypeError:
        return False
