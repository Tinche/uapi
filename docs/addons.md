# Addons

_uapi_ ships with several useful addons.

## uapi.sessions.redis async sessions

```{note}
This addon handles server-side sessions, which are anonymous by default.
If you're looking for login functionality, see [uapi.login](#uapilogin) which builds on top of sessions.
```

The `uapi.sessions.redis.configure_async_sessions` addon enables the use of cookie sessions using Redis as the session store.
This addon requires the use of an aioredis 1.3 connection pool.

First, configure the addon by giving it your `app` instance and optionally overridding parameters:

```python
from uapi.sessions.redis import configure_async_sessions

configure_async_sessions(app, redis, )
```

## uapi.login

The `uapi.login` addon enables login/logout for _uapi_ apps.
