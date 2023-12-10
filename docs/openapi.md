# OpenAPI

_uapi_ can generate and serve an OpenAPI schema for your API.

```python
from uapi import App

app = App()

# Register your routes here

# Serve the schema at /openapi.json by default
app.serve_openapi()

# Generate the schema, if you want to access it directly or customize it
spec = app.make_openapi_spec()
```

Additionally, _uapi_ also supports serving several OpenAPI documentation viewers:

```python
app.serve_swaggerui()
app.serve_redoc()
app.serve_elements()
```

The documentation viewer will be available at its default URL.

```{seealso}
{meth}`App.serve_swaggerui() <uapi.base.App.serve_swaggerui>`

{meth}`App.serve_redoc() <uapi.base.App.serve_redoc>`

{meth}`App.serve_elements() <uapi.base.App.serve_elements>`
```

What is referred to as _routes_ in _uapi_, OpenAPI refers to as _operations_.
This document uses the _uapi_ nomenclature by default.

_uapi_ comes with OpenAPI schema support for the following types:

- strings
- integers
- booleans
- floats (`type: number, format: double`)
- bytes (`type: string, format: binary`)
- dates (`type: string, format: date`)
- datetimes (`type: string, format: date-time`)

## Operation Summaries and Descriptions

OpenAPI allows operations to have summaries and descriptions; summaries are usually used as operation labels in OpenAPI tooling.

By default, uapi generates summaries from [route names](handlers.md#route-names).
This can be customized by using your own summary transformer, which is a function taking the actual handler function or coroutine and the route name, and returning the summary string.

```python
app = App()

def summary_transformer(handler: Callable, name: str) -> str:
    """Use the name of the handler function as the summary."""
    return handler.__name__

app.serve_openapi(summary_transformer=summary_transformer)
```

Operation descriptions are generated from handler docstrings by default.
This can again be customized by supplying your own description transformer, with the same signature as the summary transformer.

```python
app = App()

def desc_transformer(handler: Callable, name: str) -> str:
    """Use the first line of the docstring as the description."""
    doc = getattr(handler, "__doc__", None)
    if doc is not None:
        return doc.split("\n")[0]
    return None

app.serve_openapi(description_transformer=desc_transformer)
```


OpenAPI allows Markdown to be used for descriptions.

## Endpoint Tags

OpenAPI supports grouping endpoints by tags.
You can specify tags for each route when registering it:

```python
@app.get("/{article_id}", tags=["articles"])
async def get_article(article_id: str) -> str:
    return "Getting the article"
```

Depending on the OpenAPI visualization framework used, operations with tags are usually displayed grouped under the tag.
