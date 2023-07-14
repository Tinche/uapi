from collections.abc import Callable, Sequence
from typing import Literal, TypeAlias, TypeVar

R = TypeVar("R")
CB = Callable[..., R]

RouteName: TypeAlias = str
RouteTags: TypeAlias = Sequence[str]
Method: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
Routes: TypeAlias = dict[tuple[Method, str], tuple[Callable, RouteName, RouteTags]]
PathParamParser: TypeAlias = Callable[[str], tuple[str, list[str]]]


def is_subclass(cls, subclass) -> bool:
    """A more robust version."""
    try:
        return issubclass(cls, subclass)
    except TypeError:
        return False
