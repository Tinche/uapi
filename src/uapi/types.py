from collections.abc import Callable, Sequence
from typing import Literal, NewType, TypeAlias, TypeVar

R = TypeVar("R")
CB = Callable[..., R]

#: The route name.
RouteName = NewType("RouteName", str)

RouteTags: TypeAlias = Sequence[str]

#: The HTTP request method.
Method: TypeAlias = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]

PathParamParser: TypeAlias = Callable[[str], tuple[str, list[str]]]
