from typing import Callable, Optional, Union

from attr import frozen


@frozen
class Header:
    name: str


@frozen
class Cookie:
    name: Optional[str] = None


Parameter = Union[Header]


def parameters(**kwargs: Parameter) -> Callable[[Callable], Callable]:
    def inner(fn: Callable) -> Callable:
        fn.__attrs_api_meta__ = kwargs  # type: ignore
        return fn

    return inner
