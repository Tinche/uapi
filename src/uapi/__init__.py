from .cookies import Cookie
from .requests import Header, ReqBody
from .responses import ResponseException
from .status import Found, Headers, SeeOther

__all__ = [
    "Cookie",
    "Header",
    "ReqBody",
    "ResponseException",
    "redirect",
    "redirect_to_get",
]


def redirect(location: str, headers: Headers = {}) -> Found[None]:
    return Found(None, headers | {"Location": location})


def redirect_to_get(location: str, headers: Headers = {}) -> SeeOther[None]:
    return SeeOther(None, headers | {"Location": location})
