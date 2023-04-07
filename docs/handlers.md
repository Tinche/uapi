# Writing Handlers

Handlers are your functions and coroutines that _uapi_ calls to process incoming requests.

We **strongly recommend** not using async handlers with Flask or Django unless you know what you're doing, even though (technically) all supported frameworks support both sync and async handlers.

## Receiving Data

### Path Parameters

The first way to get data into a handler is by using _path parameters_.
A path parameter is inserted into the _handler route string_, and the value of the parameter is given to the handler.
Since the routing is left to the underlying framework, the format of the route string is framework-specific.

The path parameter in the route string and the name of the handler argument must match.
The type annotation is not examined; all frameworks default to string path parameters.

````{tab} Starlette

```python
@app.get("/{article_id}")
async def get_article(article_id: str) -> str:
    return "Getting the article"
```

Starlette uses curly brackets for path parameters and supports [several built-in converters](https://www.starlette.io/routing/).

````

````{tab} Flask

```python
@app.get("/<article_id>")
def get_article(article_id: str) -> str:
    return "Getting the article"
```

Flask uses angle brackets for path parameters and supports [several built-in converters](https://flask.palletsprojects.com/en/latest/quickstart/#variable-rules).

````

````{tab} Quart

```python
@app.get("/<article_id>")
async def get_article(article_id: str) -> str:
    return "Getting the article"
```

Quart uses angle brackets for path parameters and supports [several built-in converters](https://pgjones.gitlab.io/quart/how_to_guides/routing.html#converters).

````

````{tab} Django

```python
@app.get("/<article_id>")
async def get_article(article_id: str) -> str:
    return "Getting the article"
```

Django uses angle brackets for path parameters and come with [several built-in converters](https://docs.djangoproject.com/en/4.1/topics/http/urls/#path-converters), alongside the ability to add your own.

````

````{tab} Aiohttp

```python
@app.get("/{article_id}")
async def get_article(article_id: str) -> str:
    return "Getting the article"
```

Aiohttp uses curly brackets for path parameters and only supports strings.

````

### JSON Request Bodies

If the HTTP request body data is a JSON object, it should be modeled as an _attrs_ class and declared as a `ReqBody` parameter in the handler.

```python
from attrs import define

@define
class Article:
    article_id: str

@app.post("/article")
async def create_article(article: ReqBody[Article]) -> None:
    # `article` is an instance of `Article`
    ...
```

```{note}
A parameter annotated as a `ReqBody[T]` will be equivalent to `T` in the function body.

`ReqBody[T]` is an easier way of saying `typing.Annotated[T, JsonReqLoader()]`, and `typing.Annotated` is a way to add metadata to a type.
```

If the request body cannot be loaded into the given model, a `400 Bad Request` response will be returned instead.
This can be customized by providing your own own instance of {py:class}`uapi.requests.JsonBodyLoader` with a custom `error_handler`.

```python
from typing import Annotated, TypeVar
from uapi.requests import JsonBodyLoader
from uapi.status import BadRequest

T = TypeVar("T")

def make_error_response(exc: Exception, bytes: payload) -> BadRequest[None]:
    # Examine the exception.
    return BadRequest("Bad payload buddy")

MyErrorReqBody = Annotated[T, JsonBodyLoader(error_handler=make_error_response)]

@app.post("/endpoint")
async def create_article(article: MyErrorReqBody[Article]) -> None:
    # `article` is an instance of `Article`
    ...
```

The handler requires the caller to set the `content-type` header to `application/json`; a `415 Unsupported Media Type` error will be returned otherwise.
This is a security feature, helping with some forms of [CSRF](https://owasp.org/www-community/attacks/csrf).

Custom values for `content-type` can be required by providing your own instance of {py:class}`uapi.requests.JsonBodyLoader`.

```python
from typing import Annotated, TypeVar
from uapi.requests import JsonBodyLoader

T = TypeVar("T")

MyReqBody = Annotated[T, JsonBodyLoader("application/vnd.myapp.v1+json")]

@app.post("/endpoint")
async def create_article(article: MyReqBody[Article]) -> None:
    # `article` is an instance of `Article`
    ...

```

Content type validation can be disabled by passing `None` to the `JsonBodyLoader`; the `content-type` header will be ignored.
This in inadvisable unless you have no other choice.

### Headers

HTTP headers are injected into your handlers when one or more of your handler parameters are annotated using `uapi.Header[T]`.

```{tip}
Technically, HTTP requests may contain several headers of the same name.
All underlying frameworks return the *first* value encountered.
```

```python
from uapi import Header


@app.post("/login")
async def login(session_token: Header[str]) -> None:
    # `session_token` is a `str`
    ...

```

By default, the name of the header is the name of the handler parameter with underscores replaced by dashes.
(So, in the above example, the expected header name is `session-token`.)

If the header parameter has no default and the header is not present in the request, the resulting scenario
is left to the underlying framework. The current options are:

- Quart: a response with status `400` is returned
- All others: a response with status `500` is returned

`uapi.Header[T]` is equivalent to `Annotated[T, uapi.HeaderSpec]`, and header behavior can be customized
by providing your own instance of {py:class}`uapi.requests.HeaderSpec`.

For example, the header name can be customized on a case-by-case basis like this:

```python
from typing import Annotated
from uapi import HeaderSpec


@app.post("/login")
async def login(session_token: Annotated[str, HeaderSpec("my_header")]) -> None:
    # `session_token` is a `str`
    ...

```

Headers may have defaults which will be used if the header is not present in the request.
Headers with defaults will be rendered as `required=False` in the OpenAPI schema.

```python
@app.post("/login")
async def login(session_token: Header[str | None] = None) -> None:
    # `session_token` is a `str | None`
    ...

```

Header types may be strings or anything else. Strings are provided directly by
the underlying frameworks, any other type is produced by structuring the string value
into that type using the App _cattrs_ `Converter`.

### Framework-specific Request Objects

In case _uapi_ doesn't cover your exact needs, your handler can be given the request object provided by your underlying framework.
Annotate a handler parameter with your framework's request type.

These parameters cannot be inspected by _uapi_ so they won't show up in the OpenAPI schema.
Additionally, they tie your handlers to a specific underlying framework making your handlers less portable.
They can, however, help in incrementally porting to _uapi_.

````{tab} Starlette

```python
from starlette.requests import Request

@app.get("/")
async def get_root(req: Request) -> None:
    # Do something with `req`
    return
```

````

````{tab} Flask

```python
from flask import request

@app.get("/")
def get_root() -> None:
    # Do something with `request`
    return
```

Flask uses the usual ``flask.request`` threadlocal object for the request, so no handler parameter is necessary.

````

````{tab} Quart

```python
from quart import request

@app.get("/")
async def get_root() -> None:
    # Do something with `request`
    return
```

Quart uses the usual ``quart.request`` contextvar object for the request, so no handler parameter is necessary.

````

````{tab} Django

```python
from django.http import HttpRequest

@app.get("/")
def get_root(req: HttpRequest) -> None:
    # Do something with `req`
    return
```

````

````{tab} Aiohttp

```python
from aiohttp.web import Request

@app.get("/")
async def get_root(req: Request) -> None:
    # Do something with `req`
    return
```

````

## Returning Data

### Nothing `(204 No Content)`

If your handler returns no data, annotate the return type as `None`.

```python
@app.delete("/article")
async def delete_article() -> None:
    ... # Perform side-effects.
```

```{tip}
Whether the response contains the `content-type` header is up to the underlying framework.

Flask, Quart and Django add a `text/html` content type by default.
```

A longer equivalent, with the added benefit of being able to specify response headers, is returning the {py:class}`NoContent <uapi.status.NoContent>` response explicitly.

```python
from uapi.status import NoContent

@app.delete("/article")
async def delete_article() -> NoContent:
    # Perform side-effects.
    return NoContent(headers={"key": "value"})
```

### Strings and Bytes `(200 OK)`

If your handler returns a string or bytes, the response will be returned directly alongside the `200 OK` status code.

```python
@app.get("/article/image")
async def get_article_image() -> bytes:
    ...
```

For strings, the `content-type` header is set to `text/plain`, and for bytes to `application/octet-stream`.

### Framework-specific Response Objects

If you need to return your framework's native response class, you can.

These responses cannot be inspected by _uapi_ so they won't show up in the OpenAPI schema.
Additionally, they tie your handlers to a specific underlying framework making your handlers less portable.
They can, however, help in incrementally porting to _uapi_.

````{tab} Starlette

```python
from starlette.responses import PlainTextResponse

@app.get("/")
async def get_root() -> PlainTextResponse:
    return PlainTextResponse("content")
```

````

````{tab} Flask

```python
from flask import Response

@app.get("/")
def get_root() -> Response:
    return Response("content")
```

````

````{tab} Quart

```python
from quart import Response

@app.get("/")
async def get_root() -> Response:
    return Response("content")
```

````

````{tab} Django

```python
from django.http import HttpResponse

@app.get("/")
def get_root() -> HttpResponse:
    return HttpResponse("content")
```

````

````{tab} Aiohttp

```python
from aiohttp.web import Response

@app.get("/")
async def get_root() -> Response:
    return Response(body="content")
```

````
