# Handler Composition Context

Handlers and middleware may be composed with the results of other functions (and coroutines, when using an async framework); this is commonly known as dependency injection.
The composition context is a set of rules governing how and when this happens.
_uapi_ uses the [_Incant_](https://incant.threeofwands.com) library for function composition.

_uapi_ includes a number of composition rules by default, but users and third-party middleware are encouraged to define their own rules.

## Path and Query Parameters

Path and query parameters can be provided to handlers and middleware, see [](handlers.md#query-parameters) and [](handlers.md#path-parameters) for details.

## Headers

Headers can be provided to handlers and middleware, see [](handlers.md#headers) for details.

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
