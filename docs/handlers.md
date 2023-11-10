```{currentmodule} uapi.base

```

# Writing Handlers

Handlers are your functions and coroutines that _uapi_ calls to process incoming requests.

Handlers are registered to apps using {meth}`App.route`, or helper decorators like {meth}`App.get` and {meth}`App.post`.

```python
@app.get("/")
async def index() -> None:
    return

# Alternatively,
app.route("/", index, methods=["GET"])
```

We **strongly recommend** not using async handlers with Flask or Django unless you know what you're doing, even though (technically) all supported frameworks support both sync and async handlers.

## Handler Names

Each handler is registered under a certain _name_.
The name is a simple string identifying the handler, and defaults to the name of the handler function or coroutine.
Names are propagated to the underlying frameworks, where they have framework-specific purposes.

Names are also used in the generated OpenAPI schema:

- to generate the operation summary
- as the `operationId` Operation property property

Names should be unique across handlers and methods, so if you want to register the same handler for two methods you will need to specify one of the names manually.

```python
@app.get("/")
@app.post("/", name="post-multipurpose-handler")
async def multipurpose_handler() -> None:
    return
```

## Receiving Data

### Query Parameters

To receive query parameters, annotate a handler parameter with any type that hasn't been overriden and is not a [path parameter](handlers.md#path-parameters).
The {py:class}`App <uapi.base.App>`'s dependency injection system is configured to fulfill handler parameters from query parameters by default; directly when annotated as strings or Any or through the App's converter if any other type.
Query parameters may have default values.

Query params will be present in the [OpenAPI schema](openapi.md); parameters with defaults will be rendered as `required=False`.

```python
@app.get("/query_handler")
async def query_handler(string_query: str, int_query: int = 0) -> None:
    # The int_query param will be the result of `app.converter.structure(int_query, int)`
    return
```

### Path Parameters

One of the simplest ways of getting data into a handler is by using _path parameters_.
A path parameter is inserted into the _handler route string_ and the value of the parameter is given to the handler.
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

In addition, the request body may be modeled as a `dict` of `str` to a primitive type or an _attrs_ class.

```python
@app.post("/articles")
async def create_articles(articles: ReqBody[dict[str, Article]]) -> None:
    ...
```

### Headers

HTTP headers are provided to your handlers when one or more of your handler parameters are annotated using {class}`uapi.Header[T] <uapi.requests.Header>`.

```{note}
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

{class}`uapi.Header[T] <uapi.requests.Header>` is equivalent to `Annotated[T, uapi.HeaderSpec]`, and header behavior can be customized
by providing your own instance of {class}`uapi.requests.HeaderSpec`.

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

### Cookies

Cookies are provided to your handlers when one or more of your handler parameters are annotated using {class}`uapi.Cookie <uapi.cookies.Cookie>`, which is a subclass of `str`.
By default, the name of the cookie is the exact name of the handler parameter.

```python
from uapi import Cookie


@app.post("/login")
async def login(session_token: Cookie) -> None:
    # `session_token` is a `str` subclass
    ...
```

The name of the cookie can be customized on an individual basis by using `typing.Annotated`:

```python
from typing import Annotated
from uapi import Cookie


@app.post("/login")
async def login(session_token: Annotated[str, Cookie("session-token")]) -> None:
    # `session_token` is a `str` subclass, fetched from the `session-token` cookie
    ...
```

Cookies may have defaults which will be used if the cookie is not present in the request.
Cookies with defaults will be rendered as `required=False` in the OpenAPI schema.

Cookies may be set by using {meth}`uapi.cookies.set_cookie`.

```python
from uapi.status import Ok
from uapi.cookies import set_cookie

async def sets_cookies() -> Ok[str]
    return Ok("response", headers=set_cookie("my_cookie_name", "my_cookie_value"))
```

```{tip}
Since {meth}`uapi.cookies.set_cookie` returns a header mapping, multiple cookies can be set by using the `|` operator.
```

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

### _attrs_ Classes

Handlers can return an instance of an _attrs_ class.
The return value with be deserialized into JSON using the App _cattrs_ converter, which can be customized as per the usual _cattrs_ ways.

The status code will be set to `200 OK`, and the content type to `application/json`. The class will be added to the OpenAPI schema.

```python
from attrs import define

@define
class Article:
    title: str

@app.get("/article")
async def get_article() -> Article:
    ...
```

### _uapi_ Status Code Classes

_uapi_ {py:obj}`contains a variety of classes <uapi.status>`, mapping to status codes, for returning from handlers.
All of these classes also take an optional `header` parameter for response headers.

```python
from uapi.status import Ok

@app.get("/article")
async def get_article() -> Ok[Article]:
    # fetch article
    return Ok(article, headers={"my-header": "header value"})
```

### Returning Multiple Status Codes

If your handler can return multiple status codes, use a union of _uapi_ response types.

All responses defined this way will be rendered in the OpenAPI schema.

```python
@app.get("/profile")
async def user_profile() -> Ok[Profile] | NoContent:
    ...
```

### _uapi_ ResponseExceptions

Any raised instances of {class}`uapi.ResponseException` will be caught and transformed into a proper response.
Like any exception, ResponseExceptions short-circuit handlers so they can be useful for validation and middleware.
In other cases, simply returning a response instead is cheaper and usually more type-safe.

ResponseExceptions contain instances of _uapi_ status code classes and so can return rich response data, just like any normal response.

```python
from uapi import ResponseException
from uapi.status import Ok, NotFound

@app.get("/article")
async def get_article() -> Ok[Article]:
    article = await fetch_article()
    if article is None:
        raise ResponseException(NotFound("article not found"))
    ...
```

Since exceptions don't show up in the handler signature, they won't be present in the generated OpenAPI schema.
If you need them to, you can add the actual response type into the handler response signature as part of a union:

```python
from uapi import ResponseException
from uapi.status import Ok, NotFound

@app.get("/article")
async def get_article() -> Ok[Article] | NotFound[str]:
    article = await fetch_article()
    if article is None:
        raise ResponseException(NotFound("article not found"))
    ...
```

### Custom Status Codes

If you require a status code that is not included with _uapi_, you can define your own status code class like this:

```python
from typing import Literal
from uapi.status import BaseResponse, R

class TooManyRequests(BaseResponse[Literal[429], R]):
    pass

@api.get("/throttled")
async def throttled() -> Ok[None] | TooManyRequests[None]:
    return TooManyRequests(None)
```

The custom status code will be included in the generated OpenAPI schema.

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
