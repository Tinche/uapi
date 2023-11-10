from typing import Literal, TypeVar

from attrs import frozen

from .status import Headers

T1 = TypeVar("T1")
T2 = TypeVar("T2")

SameSite = Literal["strict", "lax", "none"]


@frozen
class CookieSettings:
    max_age: int | None = None  # Seconds
    http_only: bool = True
    secure: bool = True
    path: str | None = None
    domain: str | None = None
    same_site: SameSite = "lax"


def _make_cookie_header(name: str, value: str, settings: CookieSettings) -> Headers:
    val = f"{name}={value}"
    if settings.max_age is not None:
        val = f"{val}; Max-Age={settings.max_age}"
    if settings.http_only:
        val = f"{val}; HttpOnly"
    if settings.secure:
        val = f"{val}; Secure"
    if settings.path is not None:
        val = f"{val}; Path={settings.path}"
    if settings.domain is not None:
        val = f"{val}; Domain={settings.domain}"
    if settings.same_site != "lax":
        val = f"{val}; SameSite={settings.same_site}"
    return {f"__cookie_{name}": val}


def _make_delete_cookie_header(name: str) -> dict:
    val = f"{name}=0; expires=Thu, 01 Jan 1970 00:00:00 GMT;"
    return {f"__cookie_{name}": val}


#: A cookie dependency.
class Cookie(str):
    ...


def set_cookie(
    name: str, value: str | None, settings: CookieSettings = CookieSettings()
) -> Headers:
    """
    Produce headers that should be returned as part of a response to set the cookie.

    :param value: When `None`, the cookie will be deleted.
    """
    return (
        _make_cookie_header(name, value, settings)
        if value is not None
        else _make_delete_cookie_header(name)
    )
