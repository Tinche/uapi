from typing import Annotated, Callable, Optional, TypeVar

from itsdangerous import BadSignature, URLSafeTimedSerializer

from .. import Cookie
from ..base import App
from ..cookies import CookieSettings, set_cookie
from ..status import Headers

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class Session(dict[str, str]):
    _serialize: Callable

    def update_session(self) -> Headers:
        name, val, *settings = self._serialize(self)
        return set_cookie(name, val, settings=CookieSettings(*settings))


def configure_secure_sessions(
    app: App,
    secret_key: str,
    cookie_name: str = "session",
    salt: str = "cookie-session",
    settings: CookieSettings = CookieSettings(max_age=2678400),
):
    s = URLSafeTimedSerializer(secret_key=secret_key, salt=salt)

    def _serialize(self):
        return (
            (
                cookie_name,
                s.dumps(self),
                settings.max_age,
                settings.http_only,
                settings.secure,
                settings.path,
                settings.domain,
                settings.same_site,
            )
            if self
            else (cookie_name, None)
        )

    def get_session(
        session: Annotated[Optional[str], Cookie(cookie_name)] = None
    ) -> Session:
        if session is None:
            res = Session()
            res._serialize = _serialize
            return res
        try:
            data = s.loads(session)
        except BadSignature:
            raise

        res = Session(data)
        res._serialize = _serialize
        return res

    app.base_incant.register_hook(
        lambda p: p.name == "session" and p.annotation is Session, get_session
    )
