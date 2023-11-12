# uapi

[![Documentation](https://img.shields.io/badge/Docs-Read%20The%20Docs-black)](https://uapi.threeofwands.com)
[![Build status](https://github.com/Tinche/uapi/workflows/CI/badge.svg)](https://github.com/Tinche/uapi/actions?workflow=CI)
[![coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/Tinche/fe982b645791164107bd8f6699ed0a38/raw/covbadge.json)](https://github.com/Tinche/uapi/actions/workflows/main.yml)
[![Code style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: Apache2](https://img.shields.io/badge/license-Apache2-C06524)](https://github.com/Tinche/uapi/blob/main/LICENSE)

_uapi_ is an elegant, high-level, extremely low-overhead Python microframework for writing HTTP APIs, either synchronously or asynchronously.

_uapi_ uses a lower-level HTTP framework to run. Currently supported frameworks are aiohttp, Django, Flask, Quart, and Starlette.
An _uapi_ app can be easily integrated into an existing project based on one of these frameworks, and a pure _uapi_ project can be easily switched between them when needed.

Using _uapi_ enables you to:

- write **either async or sync** styles of handlers, depending on the underlying framework used.
- use and customize a **function composition** (dependency injection) system, based on [incant](https://incant.threeofwands.com).
- automatically **serialize and deserialize** data through [attrs](https://www.attrs.org) and [cattrs](https://catt.rs).
- generate and use **OpenAPI** descriptions of your endpoints.
- optionally **type-check** your handlers with [Mypy](https://mypy.readthedocs.io/en/stable/).
- write and use reusable and **powerful middleware**, which integrates with the OpenAPI schema.
- **integrate** with existing apps based on [Django](https://docs.djangoproject.com/en/stable/), [Starlette](https://www.starlette.io/), [Flask](https://flask.palletsprojects.com), [Quart](https://pgjones.gitlab.io/quart/) or [aiohttp](https://docs.aiohttp.org).

Here's a simple taste (install Flask and gunicorn first):

```python3
from uapi.flask import App

app = App()

@app.get("/")
def index() -> str:
    return "Index"

app.serve_openapi()
app.serve_elements()

app.run(__name__)  # Now open http://localhost:8000/elements
```

## Project Information

- [**PyPI**](https://pypi.org/project/uapi/)
- [**Source Code**](https://github.com/Tinche/uapi)
- [**Documentation**](https://uapi.threeofwands.com)
- [**Changelog**](https://uapi.threeofwands.com/en/latest/changelog.html)

## License

_uapi_ is written by [Tin Tvrtković](https://threeofwands.com/) and distributed under the terms of the [Apache-2.0](https://spdx.org/licenses/Apache-2.0.html) license.
