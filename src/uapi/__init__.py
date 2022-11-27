from attrs import frozen

from .cookies import Cookie
from .requests import ReqBody
from .responses import ResponseException
from .status import Found, Headers, SeeOther

__all__ = ["Cookie", "ReqBody", "ResponseException", "redirect", "redirect_to_get"]


@frozen
class Header:
    name: str


def redirect(location: str, headers: Headers = {}) -> Found[None]:
    return Found(None, headers | {"Location": location})


def redirect_to_get(location: str, headers: Headers = {}) -> SeeOther[None]:
    return SeeOther(None, headers | {"Location": location})
