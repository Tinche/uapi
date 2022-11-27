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

### Request Bodies

HTTP requests can contain body data.
If the body data is a JSON object, it should be modeled as an _attrs_ class and declared as a `ReqBody` parameter in the handler.

```{note}
A parameter annotated as a `ReqBody[T]` will be equivalent to just `T` in the function body.

`ReqBody[T]` is an easier way of saying `typing.Annotated[T, ...]`, and `typing.Annotated` is a way to add metadata to a type.
```

```python
from attrs import define

@define
class Article:
    article_id: str

@app.post("/article")
async def create_article(article: ReqBody[Article]) -> None:
    pass
```

The handler will require the caller to set the `content-type` header to `application/json`; a `415 Unsupported Media Type` error will be returned otherwise.
This is a security feature, helping with some forms of [CSRF](https://owasp.org/www-community/attacks/csrf).

## Returning Data
