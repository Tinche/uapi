"""Redis backends for sessions."""
from datetime import timedelta
from json import dumps, loads
from secrets import token_hex
from time import time
from typing import TYPE_CHECKING, Annotated, TypeVar

from attrs import frozen

from .. import Cookie, Headers
from ..base import App, OpenAPISecuritySpec
from ..cookies import CookieSettings, set_cookie
from ..openapi import ApiKeySecurityScheme

if TYPE_CHECKING:
    from aioredis import Redis

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class AsyncSession(dict[str, str]):
    _cookie_name: str
    _cookie_settings: CookieSettings
    _aioredis: "Redis"
    _namespace: str
    _id: str
    _ttl: int
    _key_prefix: str

    async def update_session(self, *, namespace: str | None = None) -> Headers:
        namespace = namespace or self._namespace
        if namespace is None:
            raise Exception("The namespace must be set for new sessions.")
        now = time()
        ns_key = f"{self._key_prefix}{namespace}:s"
        key = f"{ns_key}:{self._id}"
        existing_id_ttl = await self._aioredis.ttl(key)
        existing_namespace_ttl = await self._aioredis.ttl(ns_key)

        if existing_id_ttl < 0:  # Means key not found.
            existing_id_ttl = self._ttl

        pipeline = self._aioredis.pipeline()

        pipeline.set(key, dumps(self, separators=(",", ":")), expire=existing_id_ttl)
        pipeline.zadd(ns_key, now + existing_id_ttl, self._id)
        if existing_id_ttl > existing_namespace_ttl:
            pipeline.expire(ns_key, existing_id_ttl)

        await pipeline.execute()

        return set_cookie(
            self._cookie_name, f"{namespace}:{self._id}", settings=self._cookie_settings
        )

    async def clear_session(self) -> Headers:
        self.clear()
        if self._namespace is not None:
            pipeline = self._aioredis.pipeline()
            pipeline.delete(f"{self._namespace}:s:{self._id}")
            pipeline.zrem(f"{self._namespace}:s", self._id)
            await pipeline.execute()
        return set_cookie(self._cookie_name, None)


@frozen
class AsyncRedisSessionStore:
    _redis: "Redis"
    _key_prefix: str
    _cookie_name: str
    _cookie_settings: CookieSettings

    async def remove_namespace(self, namespace: str) -> None:
        """Remove all sessions in a particular namespace."""
        ns_key = f"{self._key_prefix}{namespace}:s"
        session_ids = await self._redis.zrangebyscore(ns_key, time(), float("inf"))
        pipeline = self._redis.pipeline()
        for session_id in session_ids:
            pipeline.delete(f"{ns_key}:{session_id}")
        pipeline.delete(ns_key)
        await pipeline.execute()


def configure_async_sessions(
    app: App,
    aioredis: "Redis",
    max_age: timedelta = timedelta(days=14),
    cookie_name: str = "session_id",
    cookie_settings: CookieSettings = CookieSettings(),
    redis_key_prefix: str = "",
    session_arg_param_name: str = "session",
) -> AsyncRedisSessionStore:
    """
    Configure an instance of async sessions for an app.

    A session ID will be generated using Python's `secrets.token_hex` and stored in a
    cookie.

    Once configured, handlers may declare a parameter of name _session_arg_param_name
    (defaults to `session`) and type `AsyncSession`. AsyncSessions are mappings of
    strings to strings, and can be used to store data using the
    `AsyncSession.update_session()` and `AsyncSession.clear_session()` coroutines.

    If the cookie is missing or the session data has expired, a new empty session will
    be transparently created.

    Sessions have optional namespaces. Namespaces are useful for logically grouping
    sessions, for example by user ID, so that multiple sessions can be cleared at once.

    Fresh sessions start with no namespace set. To set a namespace, pass it to
    `AsyncSession.update_session()`.

    An `AsyncRedisSessionStore` is produced at configuration time and can be used to
    clean up namespaces even outside the context of a request.

    :param max_age: The maximum age of a session. When this expires, the session is
        cleaned up from Redis.
    :param cookie_name: The name of the cookie to use for the session id.
    :param cookie_settings: The settings for the cookie.
    :param redis_key_prefix: The prefix to use for redis keys.
    :param session_arg_param_name: The name of the handler parameter that will be
        available for dependency injection.
    """
    ttl = int(max_age.total_seconds())

    async def session_factory(
        cookie: Annotated[str | None, Cookie(cookie_name)] = None
    ) -> AsyncSession:
        if cookie is not None:
            namespace, id = cookie.split(":")
            pipeline = aioredis.pipeline()
            pipeline.get(f"{redis_key_prefix}{namespace}:s:{id}")
            pipeline.zremrangebyscore(f"{redis_key_prefix}{namespace}:s", 0, time())
            payload, _ = await pipeline.execute()
            if payload is not None:
                res = AsyncSession(loads(payload))
                res._namespace = namespace
            else:
                res = None
        else:
            res = None

        if res is None:
            id = token_hex()
            res = AsyncSession()
            res._namespace = ""

        res._cookie_name = cookie_name
        res._cookie_settings = cookie_settings
        res._aioredis = aioredis
        res._ttl = ttl
        res._id = id
        res._key_prefix = redis_key_prefix
        return res

    app.incant.register_hook(
        lambda p: p.name == session_arg_param_name and p.annotation is AsyncSession,
        session_factory,
    )

    app._openapi_security.append(
        OpenAPISecuritySpec(ApiKeySecurityScheme(cookie_name, "cookie"))
    )

    return AsyncRedisSessionStore(
        aioredis, redis_key_prefix, cookie_name, cookie_settings
    )
