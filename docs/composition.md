# Handler Composition Context

Handlers and middleware may be composed with the results of other functions (and coroutines, when using an async framework); this is commonly known as dependency injection.
The composition context is a set of rules governing how and when this happens.
_uapi_ uses the [_Incant_](https://incant.threeofwands.com) library for function composition.

_uapi_ includes a number of composition rules by default, but users and third-party middleware are encouraged to define their own rules.

## Path and Query Parameters

Path and query parameters can be provided to handlers and middleware, see [](handlers.md#query-parameters) and [](handlers.md#path-parameters) for details.

## Headers and Cookies

Headers and cookies can be provided to handlers and middleware, see [](handlers.md#headers) and see [](handlers.md#cookies) for details.

## JSON Payloads as _attrs_ Classes

JSON payloads, structured into _attrs_ classes by _cattrs_, can by provided to handlers and middleware. See [](handlers.md#attrs-classes) for details.

## Route Metadata

```{tip}
_Routes_ are different than _handlers_; a single handler may be registered on multiple routes.
```

Route metadata can be provided to handlers and middleware, although it can be more useful to middleware.

- The route name will be provided if a parameter is annotated as {class}`uapi.RouteName <uapi.types.RouteName>`, which is a string-based NewType.
- The request HTTP method will be provided if a parameter is annotated as {class}`uapi.Method <uapi.types.Method>`, which is a string Literal.

Here's an example using both:

```python
from uapi import Method, RouteName

@app.get("/")
def route_name_and_method(route_name: RouteName, method: Method) -> str:
    return f"I am route {route_name}, requested with {method}"
```

## Customizing the Context

The composition context can be customized by defining and then using Incant hooks on the {class}`App.incant <uapi.base.App.incant>` Incanter instance.

For example, say you'd like to receive a token of some sort via a header, validate it and transform it into a user ID.
The handler should look like this:

```python
@app.get("/valid-header")
def non_public_handler(user_id: str) -> str:
    return "Hello {user_id}!"
```

Without any additional configuration, _uapi_ thinks the `user_id` parameter is supposed to be a mandatory [query parameter](handlers.md#query-parameters).
First, we need to create a dependency hook for our use case and register it with the App Incanter.

```python
from uapi import Header

@app.incant.register_by_name("user_id")
def validate_token_and_fetch_user(session_token: Header[str]) -> str:
    # session token value will be injected from the `session-token` header

    user_id = validate(session_token)  # Left as an exercize to the reader

    return user_id
```

Now our `non_public_handler` handler will have the validated user ID provided to it.

```{note}
Since Incant is a true function composition library, the `session-token` dependency will also show up in the generated OpenAPI schema.
This is true of all dependency hooks and middleware.

The final handler signature available to _uapi_ at time of serving contains all the dependencies as function arguments.
```

## Extending the Context

The composition context can be extended with arbitrary dependencies.

For example, imagine your application needs to perform HTTP requests.
Ideally, the handlers should use a shared connection pool instance for efficiency.
Here's a complete implementation of a very simple HTTP proxy.
The example can be pasted and ran as-is as long as Starlette and Uvicorn are available.

```python
from asyncio import run

from httpx import AsyncClient

from uapi.starlette import App

app = App()

_client = AsyncClient()  # We only want one.
app.incant.register_by_type(lambda: _client, type=AsyncClient)


@app.get("/proxy")
async def proxy(client: AsyncClient) -> str:
    """We just return the payload at www.example.com."""
    return (await client.get("http://example.com")).read().decode()


run(app.run())
```

## Integrating the `svcs` Package

If you'd like to get more serious about application architecture, one of the approaches is to use the [svcs](https://svcs.hynek.me/) library.
Here's a way of integrating it into _uapi_.

```python
from httpx import AsyncClient
from svcs import Container, Registry
from asyncio import run

from uapi.starlette import App

reg = Registry()

app = App()
app.incant.register_by_type(
    lambda: Container(reg), type=Container, is_ctx_manager="async"
)


@app.get("/proxy")
async def proxy(container: Container) -> str:
    """We just return the payload at www.example.com."""
    client = await container.aget(AsyncClient)
    return (await client.get("http://example.com")).read().decode()

async def main() -> None:
    async with AsyncClient() as client:  # Clean up connections at the end
        reg.register_value(AsyncClient, client, enter=False)
        await app.run()

run(main())
```

We can go even further and instead of providing the `container`, we can provide anything the container contains too.

```python
from collections.abc import Callable
from inspect import Parameter
from asyncio import run

from httpx import AsyncClient
from svcs import Container, Registry

from uapi.starlette import App

reg = Registry()


app = App()
app.incant.register_by_type(
    lambda: Container(reg), type=Container, is_ctx_manager="async"
)


def svcs_hook_factory(parameter: Parameter) -> Callable:
    t = parameter.annotation

    async def from_container(c: Container):
        return await c.aget(t)

    return from_container


app.incant.register_hook_factory(lambda p: p.annotation in reg, svcs_hook_factory)


@app.get("/proxy")
async def proxy(client: AsyncClient) -> str:
    """We just return the payload at www.example.com."""
    return (await client.get("http://example.com")).read().decode()


async def main() -> None:
    async with AsyncClient() as client:
        reg.register_value(AsyncClient, client, enter=False)
        await app.run()


run(main())
```

```{note}
The _svcs_ library includes integrations for several popular web frameworks, and code examples for them.
The examples shown here are independent of the underlying web framework used; they will work on all of them (with a potential sync/async tweak).
```
