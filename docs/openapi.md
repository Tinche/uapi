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

## Endpoint Tags

OpenAPI supports grouping endpoints by tags.
You can specify tags for each handler when registering it:

```python
@app.get("/{article_id}", tags=["articles"])
async def get_article(article_id: str) -> str:
    return "Getting the article"
```

Depending on the OpenAPI visualization framework used, endpoints with tags are usually displayed grouped under the tag.
