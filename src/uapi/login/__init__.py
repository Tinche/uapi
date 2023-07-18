from inspect import Signature
from typing import Generic, TypeVar

from attrs import frozen

from .. import ResponseException
from ..base import App
from ..sessions.redis import AsyncRedisSessionStore, AsyncSession
from ..status import BaseResponse, Forbidden, Headers

T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")


@frozen
class AsyncLoginManager(Generic[T]):
    async_session_store: AsyncRedisSessionStore

    async def logout(self, user_id: T) -> None:
        """Invalidate all sessions of `user_id`."""
        await self.async_session_store.remove_namespace(str(user_id))


@frozen
class AsyncLoginSession(Generic[T]):
    user_id: T | None
    _session: AsyncSession

    async def login_and_return(self, user_id: T) -> Headers:
        """Set the current session as logged with the given user ID.

        The produced headers need to be returned to the user to set the appropriate
        cookies.
        """
        self._session["user_id"] = str(user_id)
        return await self._session.update_session(namespace=str(user_id))

    async def logout_and_return(self) -> Headers:
        return await self._session.clear_session()


def configure_async_login(
    app: App,
    user_id_cls: type[T],
    redis_session_store: AsyncRedisSessionStore,
    forbidden_response: BaseResponse = Forbidden(None),
) -> AsyncLoginManager[T]:
    """Configure the app for handling login sessions.

    :param user_id_cls: The class of the user ID. Handlers will need to annotate the
        `current_user_id` parameter with this class or `user_id_cls | None`.
    """

    def user_id_factory(session: AsyncSession) -> T:
        if "user_id" in session:
            return user_id_cls(session["user_id"])  # type: ignore
        raise ResponseException(forbidden_response)

    def optional_user_id_factory(session: AsyncSession) -> T | None:
        if "user_id" in session:
            return user_id_cls(session["user_id"])  # type: ignore
        return None

    def async_login_session_factory(
        current_user_id: user_id_cls | None, session: AsyncSession  # type: ignore
    ) -> AsyncLoginSession[T]:
        return AsyncLoginSession(current_user_id, session)

    app.incant.register_hook(
        lambda p: p.name == "current_user_id"
        and p.annotation == user_id_cls
        and p.default is Signature.empty,
        user_id_factory,
    )
    app.incant.register_hook(
        lambda p: p.name == "current_user_id" and p.annotation == user_id_cls | None,
        optional_user_id_factory,
    )
    app.incant.register_hook(
        lambda p: p.name == "login_session"
        and p.annotation == AsyncLoginSession[user_id_cls],  # type: ignore
        async_login_session_factory,
    )
    return AsyncLoginManager(redis_session_store)
