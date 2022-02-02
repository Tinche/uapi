from typing import Annotated, Callable, Literal, Optional, TypeVar

from itsdangerous import BadSignature, URLSafeTimedSerializer

from . import BaseApp, Cookie
from .cookies import set_cookie

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class Session(dict[str, str]):
    _serialize: Callable

    def update_session(
        self, ret_val: T1, status: T2, headers: dict[str, str] = {}
    ) -> tuple[T1, T2, dict[str, str]]:
        return set_cookie((ret_val, status, headers), *self._serialize(self))


def configure_sessions(
    app: BaseApp,
    secret_key: str,
    cookie_name: str = "session",
    salt: str = "cookie-session",
    max_age: Optional[int] = 2678400,
    http_only: bool = True,
    secure: bool = True,
    path: Optional[str] = None,
    domain: Optional[str] = None,
    same_site: Literal["strict", "lax", "none"] = "lax",
):
    s = URLSafeTimedSerializer(secret_key=secret_key, salt=salt)

    def _serialize(self):
        return (
            (
                cookie_name,
                s.dumps(self),
                max_age,
                http_only,
                secure,
                path,
                domain,
                same_site,
            )
            if self
            else (cookie_name, None)
        )

    def get_session(
        session: Annotated[Optional[str], Cookie(cookie_name)] = None
    ) -> Session:
        if session is None:
            res = Session()
            res._serialize = _serialize  # type: ignore
            return res
        try:
            data = s.loads(session)
        except BadSignature:
            raise

        res = Session(data)
        res._serialize = _serialize  # type: ignore
        return res

    app.base_incant.register_hook(
        lambda p: p.name == "session" and p.annotation is Session, get_session
    )
