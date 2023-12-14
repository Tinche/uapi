```{currentmodule} uapi.shorthands

```
# Response Shorthands

Custom response shorthands are created by defining a custom instance of the {class}`ResponseShorthand` protocol.
This involves implementing two to four functions, depending on the amount of functionality required.

## A `datetime.datetime` Shorthand

Here are the steps needed to implement a new shorthand, enabling handlers to return [`datetime.datetime`](https://docs.python.org/3/library/datetime.html#datetime-objects) instances directly.

First, we need to create the shorthand class by subclassing the {class}`ResponseShorthand` generic protocol.

```python
from datetime import datetime

from uapi.shorthands import ResponseShorthand

class DatetimeShorthand(ResponseShorthand[datetime]):
    pass
```

Note that the shorthand is generic over the type we want to enable.
This protocol contains four static methods (functions); two mandatory ones and two optional ones.

The first function we need to override is {meth}`ResponseShorthand.response_adapter`.
This functions needs to convert an instance of our type (`datetime`) into a _uapi_ [status code class](handlers.md#uapi-status-code-classes), so _uapi_ can adapt the value for the underlying framework.

```python
from uapi.status import BaseResponse, Ok

class DatetimeShorthand(ResponseShorthand[datetime]):

    @staticmethod
    def response_adapter(value: Any) -> BaseResponse:
        return Ok(value.isoformat(), headers={"content-type": "date"})
```

The second function is {meth}`ResponseShorthand.is_union_member`.
This function is used to recognize if a return value is an instance of the shorthand type when the return type is a union.
For example, if the return type is `datetime | str`, uapi needs to be able to detect and handle both cases.

```python
class DatetimeShorthand(ResponseShorthand[datetime]):

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return isinstance(value, datetime)
```

With these two functions we have a minimal shorthand implementation.
We can add it to an app to be able to use it:

```
from uapi.starlette import App  # Or any other app

app = App()

app = app.add_response_shorthand(DatetimeShorthand)
```

And we're done.

### OpenAPI Integration

If we stop here our shorthand won't show up in the [generated OpenAPI schema](openapi.md).
To enable OpenAPI integration we need to implement one more function, {meth}`ResponseShorthand.make_openapi_response`.

This function returns the [OpenAPI response definition](https://swagger.io/specification/#responses-object) for the shorthand.

```python
from uapi.openapi import MediaType, Response, Schema

class DatetimeShorthand(ResponseShorthand[datetime]):

    @staticmethod
    def make_openapi_response() -> Response:
        return Response(
            "OK",
            {"date": MediaType(Schema(Schema.Type.STRING, format="datetime"))},
        )
```

### Custom Type Matching

Registered shorthands are matched to handler return types using simple identity and [`issubclass`](https://docs.python.org/3/library/functions.html#issubclass) checks.
Sometimes, more sophisticated matching is required.

For example, the default {class}`NoneShorthand <NoneShorthand>` shorthand wouldn't work for some handlers without custom matching since it needs to match both `None` and `NoneType`. This matching can be customized by overriding the {meth}`ResponseShorthand.can_handle` function.

Here's what a dummy implementation would look like for our `DatetimeShorthand`.

```python
class DatetimeShorthand(ResponseShorthand[datetime]):

    @staticmethod
    def can_handle(type: Any) -> bool:
        return issubclass(type, datetime)
```