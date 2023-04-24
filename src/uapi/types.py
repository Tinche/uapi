from typing import Callable, Literal, TypeAlias, TypeVar

R = TypeVar("R")
CB = Callable[..., R]

Method: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]
Routes: TypeAlias = dict[tuple[Method, str], tuple[Callable, str]]
PathParamParser: TypeAlias = Callable[[str], tuple[str, list[str]]]


def is_subclass(cls, subclass) -> bool:
    """A more robust version."""
    try:
        return issubclass(cls, subclass)
    except TypeError:
        return False
