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
