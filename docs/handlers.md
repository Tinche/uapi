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

## Returning Data
