from enum import Enum
from inspect import Parameter
from typing import Annotated, Any, Callable, NewType, Optional, TypeAlias, TypeVar

from attrs import has
from cattrs import Converter
from cattrs._compat import get_args, is_annotated

try:
    from orjson import loads
except ImportError:
    from json import loads

from . import Cookie

T = TypeVar("T")
RequestLoaderPredicate: TypeAlias = Callable[[Parameter], bool]


class Sentinels(Enum):
    REQ_BODY = "request_body"


ReqBodySentinel = Sentinels.REQ_BODY
ReqBody = Annotated[T, ReqBodySentinel]
ReqBytes = NewType("ReqBytes", bytes)


def make_json_loader(
    annotated_sentinel: Any, converter: Converter
) -> tuple[RequestLoaderPredicate, Callable]:
    def maybe_req_body_attrs(p: Parameter) -> type | None:
        t = p.annotation
        if is_annotated(t):
            args = get_args(t)
            if args and has(args[0]):
                for arg in args[1:]:
                    if arg is annotated_sentinel:
                        return args[0]
        return None

    def is_req_body_attrs(p: Parameter) -> bool:
        return maybe_req_body_attrs(p) is not None

    def get_req_body_attrs(p: Parameter) -> type:
        """Similar to `maybe_req_body_attrs`, except raises."""
        res = maybe_req_body_attrs(p)
        if res is None:
            raise Exception("No attrs request body found")
        return res

    def attrs_body_factory(attrs_cls: type[T], _c=converter) -> Callable[[ReqBytes], T]:
        def structure_body(body: ReqBytes) -> T:
            return _c.structure(loads(body), attrs_cls)

        return structure_body

    return is_req_body_attrs, lambda p: attrs_body_factory(get_req_body_attrs(p))


def get_cookie_name(t, arg_name: str) -> Optional[str]:
    if t is Cookie or t is Optional[Cookie]:
        return arg_name
    elif is_annotated(t):
        for arg in get_args(t)[1:]:
            if arg.__class__ is Cookie:
                return arg or arg_name
    return None


def maybe_req_body_attrs(p: Parameter) -> type | None:
    t = p.annotation
    if is_annotated(t):
        args = get_args(t)
        if args and has(args[0]):
            for arg in args[1:]:
                if arg is ReqBodySentinel:
                    return args[0]
    return None


def get_req_body_attrs(p: Parameter) -> type:
    """Similar to `maybe_req_body_attrs`, except raises."""
    res = maybe_req_body_attrs(p)
    if res is None:
        raise Exception("No attrs request body found")
    return res


def is_req_body_attrs(p: Parameter) -> bool:
    return maybe_req_body_attrs(p) is not None
