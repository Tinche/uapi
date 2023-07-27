# OpenAPI

_uapi_ can generate and serve an OpenAPI schema for your API.

```python
from uapi import App

app = App()

# Register your routes here

# Generate the schema, if you want to access it directly
spec = app.make_openapi_spec()

# Serve the schema at /openapi.json by default
app.serve_openapi()
```

Additionally, _uapi_ also supports serving several OpenAPI documentation viewers:

```python
app.serve_swaggerui()
app.serve_redoc()
app.serve_elements()
```

The documentation viewer will be available at its default URL.

```{seealso}
{py:meth}`App.serve_swaggerui() <uapi.base.App.serve_swaggerui>`

{py:meth}`App.serve_redoc() <uapi.base.App.serve_redoc>`

{py:meth}`App.serve_elements() <uapi.base.App.serve_elements>`
```

What is referred to as _handlers_ in _uapi_, OpenAPI refers to as _operations_.
This document uses the _uapi_ nomenclature by default.

## Handler Summaries and Descriptions

OpenAPI allows handlers to have summaries and descriptions; summaries are usually used as operation labels in OpenAPI tooling.

By default, uapi generates summaries from [handler names](handlers.md#handler-names).
This can be customized by using your own summary transformer, which is a function taking the actual handler function or coroutine and the handler name, and returning the summary string.

```python
app = App()

def summary_transformer(handler: Callable, name: str) -> str:
    """Use the name of the handler function as the summary."""
    return handler.__name__

app.serve_openapi(summary_transformer=summary_transformer)
```

Handler descriptions are generated from handler docstrings by default. 
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
You can specify tags for each handler when registering it:

```python
@app.get("/{article_id}", tags=["articles"])
async def get_article(article_id: str) -> str:
    return "Getting the article"
```

Depending on the OpenAPI visualization framework used, endpoints with tags are usually displayed grouped under the tag.
