# uapi

---

`uapi` is a high-level, extremely fast Python microframework for writing HTTP APIs, either synchronously or asynchronously.

```python3
from asyncio import run
from uapi.starlette import App

app = App()

@app.get("/")
async def index() -> str:
    return "Index"

run(app.run())
```

`uapi` uses a lower-level HTTP framework to run. Currently supported frameworks are aiohttp, Flask, Quart, and Starlette.
An `uapi` app can be easily integrated into an existing project based on one of these frameworks, and a pure `uapi` project can be
easily switched between them when needed.

`uapi` supports OpenAPI out of the box.

```python3
from uapi.flask import App

app = App()

@app.get("/")
def index() -> str:
    return "Index"

app.serve_openapi()
app.serve_elements()

app.run()  # Now open http://localhost:8000/elements
```
