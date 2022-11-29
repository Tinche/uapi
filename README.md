# uapi

[![Build status](https://github.com/Tinche/uapi/workflows/CI/badge.svg)](https://github.com/Tinche/uapi/actions?workflow=CI)
[![codecov](https://codecov.io/gh/Tinche/uapi/branch/main/graph/badge.svg?token=XGKYSILAG4)](https://codecov.io/gh/Tinche/uapi)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

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

Documentation is available at https://uapi-docs.readthedocs.io/en/latest/.

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

run(app.run())  # Now open http://localhost:8000/elements
```
