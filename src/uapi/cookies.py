from typing import Literal, Optional, Tuple, TypeVar

from attrs import frozen

T1 = TypeVar("T1")
T2 = TypeVar("T2")

DELETE_EXPIRES = "Thu, 01 Jan 1970 00:00:00 GMT;"
SameSite = Literal["strict", "lax", "none"]


@frozen
class CookieSettings:
    max_age: Optional[int] = None
    http_only: bool = True
    secure: bool = True
    path: Optional[str] = None
    domain: Optional[str] = None
    same_site: SameSite = "lax"


def _make_cookie_header(
    name: str,
    value: str,
    settings: CookieSettings,
) -> dict:
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
    val = f"{name}=0; expires={DELETE_EXPIRES}"
    return {f"__cookie_{name}": val}


class Cookie(str):
    ...


def set_cookie(
    resp: Tuple[T1, T2, dict[str, str]],
    name: str,
    value: Optional[str],
    settings: CookieSettings = CookieSettings(),
) -> Tuple[T1, T2, dict[str, str]]:
    return (
        resp[0],
        resp[1],
        resp[2]
        | (
            _make_cookie_header(name, value, settings)
            if value is not None
            else _make_delete_cookie_header(name)
        ),
    )
