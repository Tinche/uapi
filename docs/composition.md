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
