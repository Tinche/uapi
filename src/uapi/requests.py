from inspect import Parameter
from typing import Annotated, Any, Optional, TypeVar

from attrs import has
from cattrs._compat import get_args, is_annotated

from . import Cookie

T = TypeVar("T")

ReqBodySentinel = object()
ReqBody = Annotated[T, ReqBodySentinel]


def is_req_body_bytes(t: Any) -> bool:
    if is_annotated(t):
        args = get_args(t)
        if args[0] is bytes:
            for arg in args[1:]:
                if arg is ReqBodySentinel:
                    return True
    return False


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


def get_cookie_name(t, arg_name: str) -> Optional[str]:
    if t is Cookie or t is Optional[Cookie]:
        return arg_name
    elif is_annotated(t):
        for arg in get_args(t)[1:]:
            if arg.__class__ is Cookie:
                return arg or arg_name
    return None
