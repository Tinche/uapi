# Addons

_uapi_ ships with several useful addons.

## Redis Async Sessions

```{note}
This addon handles server-side sessions, which are anonymous by default.
If you're looking for login functionality, see [uapi.login](#uapilogin) which builds on top of sessions.
```

The {meth}`uapi.sessions.redis.configure_async_sessions` addon enables the use of cookie sessions using Redis as the session store.
This addon requires the use of an [aioredis 1.3](https://pypi.org/project/aioredis/1.3.1/) connection pool.

First, configure the addon by giving it your `app` instance and optionally overridding parameters:

```python
from aioredis import create_pool
from uapi.sessions.redis import configure_async_sessions

session_store = configure_async_sessions(app, await create_pool(...))
```

Once configured, handlers may declare a parameter of type {class}`uapi.sessions.redis.AsyncSession`.
The session object is a `dict[str, str]` subclass, and it needs to have the {meth}`uapi.sessions.redis.AsyncSession.update_session()` coroutine called to actually store the session.

```python
async def my_session_handler(session: AsyncSession) -> None:
    session['my_key'] = 'value'
    await session.update_session()
```

Multiple sessions using multiple cookies can be configured in parallel.
If this is the case, the `session_arg_param_name` argument can be used to customize the name of the session parameter being injected.

```python
another_session_store = configure_async_sessions(
    app, 
    redis, 
    cookie_name="another_session_cookie", 
    session_arg_param_name="another_session",
)

async def a_different_handler(another_session: AsyncSession) -> None:
    session['my_key'] = 'value'
    await another_session.update_session()
```

## uapi.login

The {meth}`uapi.login.configure_async_login` addon enables login/logout for _uapi_ apps.

The _login_ addon requires a configured session store.
Then, assuming our user IDs are ints:

```python
from uapi.login import configure_async_login

login_manager = configure_async_login(app, int, session_store)
```

You'll need a login endpoint:

```python
from uapi.login import AsyncLoginSession

async def login(login_session: AsyncLoginSession) -> Ok[None]:
    if login_session.user_id is not None:
        # Looks like this session is already associated with a user.
        return Ok(None)

    # Check credentials, like a password or token
    return Ok(None, await login_session.login_and_return(user_id))
```

Now your app's handlers can declare the `current_user_id` parameter for dependency injection:

```python
async def requires_logged_in_user(current_user_id: int) -> None:
    pass
```

An unauthenticated request will be denied with a `Forbidden` response.

A user can be logged out using {meth}`uapi.login.AsyncLoginManager.logout`.

```python
async def logout_user() -> None:
    await login_manager.logout(user_id)
```
