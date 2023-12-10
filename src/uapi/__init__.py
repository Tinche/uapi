from .cookies import Cookie
from .requests import FormBody, Header, HeaderSpec, ReqBody, ReqBytes
from .responses import ResponseException
from .status import Found, Headers, SeeOther
from .types import Method, RouteName

__all__ = [
    "Cookie",
    "FormBody",
    "Header",
    "HeaderSpec",
    "Method",
    "redirect_to_get",
    "redirect",
    "ReqBody",
    "ReqBytes",
    "ResponseException",
    "RouteName",
]


def redirect(location: str, headers: Headers = {}) -> Found[None]:
    return Found(None, headers | {"Location": location})


def redirect_to_get(location: str, headers: Headers = {}) -> SeeOther[None]:
    return SeeOther(None, headers | {"Location": location})
