from .cookies import Cookie
from .requests import Header, HeaderSpec, ReqBody, ReqBytes
from .responses import ResponseException
from .status import Found, Headers, SeeOther
from .types import Method, RouteName

__all__ = [
    "Cookie",
    "Header",
    "HeaderSpec",
    "redirect_to_get",
    "redirect",
    "ReqBody",
    "ReqBytes",
    "ResponseException",
    "RouteName",
    "Method",
]


def redirect(location: str, headers: Headers = {}) -> Found[None]:
    return Found(None, headers | {"Location": location})


def redirect_to_get(location: str, headers: Headers = {}) -> SeeOther[None]:
    return SeeOther(None, headers | {"Location": location})
