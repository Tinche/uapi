from inspect import Signature
from typing import Generic, Optional, TypeVar

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

    async def logout(self, user_id: T):
        await self.async_session_store.remove_namespace(str(user_id))


@frozen
class AsyncLoginSession(Generic[T]):
    user_id: Optional[T]
    _session: AsyncSession

    async def login_and_return(self, user_id: T) -> Headers:
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
    def user_id_factory(session: AsyncSession) -> T:
        if "user_id" in session:
            return user_id_cls(session["user_id"])  # type: ignore
        else:
            raise ResponseException(forbidden_response)

    def optional_user_id_factory(session: AsyncSession) -> Optional[T]:
        if "user_id" in session:
            return user_id_cls(session["user_id"])  # type: ignore
        else:
            return None

    def async_login_session_factory(
        current_user_id: Optional[user_id_cls], session: AsyncSession  # type: ignore
    ) -> AsyncLoginSession[T]:
        return AsyncLoginSession(current_user_id, session)

    app.base_incant.register_hook(
        lambda p: p.name == "current_user_id"
        and p.annotation is user_id_cls
        and p.default is Signature.empty,
        user_id_factory,
    )
    app.base_incant.register_hook(
        lambda p: p.name == "current_user_id" and p.annotation is Optional[user_id_cls],
        optional_user_id_factory,
    )
    app.base_incant.register_hook(
        lambda p: p.name == "login_session"
        and p.annotation == AsyncLoginSession[user_id_cls],  # type: ignore
        async_login_session_factory,
    )
    return AsyncLoginManager(redis_session_store)
