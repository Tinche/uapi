from typing import Literal, Optional, Tuple, TypeVar

T1 = TypeVar("T1")
T2 = TypeVar("T2")

DELETE_EXPIRES = "Thu, 01 Jan 1970 00:00:00 GMT;"


def _make_cookie_header(
    name: str,
    value: str,
    max_age: Optional[int] = None,
    http_only: bool = True,
    secure: bool = True,
    path: Optional[str] = None,
    domain: Optional[str] = None,
    same_site: str = "lax",
) -> dict:
    val = f"{name}={value}"
    if max_age is not None:
        val = f"{val}; Max-Age={max_age}"
    if http_only:
        val = f"{val}; HttpOnly"
    if secure:
        val = f"{val}; Secure"
    if path is not None:
        val = f"{val}; Path={path}"
    if domain is not None:
        val = f"{val}; Domain={path}"
    if same_site != "lax":
        val = f"{val}; SameSite={same_site}"
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
    max_age: Optional[int] = None,
    http_only: bool = True,
    secure: bool = True,
    path: Optional[str] = None,
    domain: Optional[str] = None,
    same_site: Literal["strict", "lax", "none"] = "lax",
) -> Tuple[T1, T2, dict[str, str]]:
    return (
        resp[0],
        resp[1],
        resp[2]
        | (
            _make_cookie_header(
                name, value, max_age, http_only, secure, path, domain, same_site
            )
            if value is not None
            else _make_delete_cookie_header(name)
        ),
    )
