from typing import Optional, Union

from attr import frozen
from cattr._compat import is_union_type
from cattr.converters import NoneType


def parse_optional(t) -> Optional[type]:
    if is_union_type(t) and len(t.__args__) == 2 and NoneType in t.__args__:
        return [a for a in t.__args__ if a is not NoneType][0]


@frozen
class Header:
    name: str


Parameter = Union[Header]


def parameters(**kwargs: Parameter):
    def inner(fn):
        fn.__attrs_api_meta__ = kwargs
        return fn

    return inner
