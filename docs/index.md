# Welcome to uapi!

```{toctree}
:maxdepth: 1
:caption: "Contents:"
:hidden:

self
handlers.md
openapi.md
changelog.md
indices.md
modules.rst
```

_uapi_ is an elegant, fast, and high-level framework for writing network services in Python 3.10 and later.

Using _uapi_ enables you to:

- write **either async or sync** styles of handlers, depending on the underlying framework used.
- use and customize a **depedency injection** system, based on [incant](https://github.com/Tinche/incant/).
- automatically **serialize and deserialize** data through [attrs](https://www.attrs.org/en/stable/) and [cattrs](https://cattrs.readthedocs.io/en/latest/).
- generate and use **OpenAPI** descriptions of your endpoints.
- optionally **type-check** your handlers with [Mypy](https://mypy.readthedocs.io/en/stable/).
- write and use **powerful middleware**.
- **integrate** with existing apps based on [Django](https://docs.djangoproject.com/en/stable/), [Starlette](https://www.starlette.io/), [Flask](https://flask.palletsprojects.com/en/latest/), [Quart](https://pgjones.gitlab.io/quart/) or [Aiohttp](https://docs.aiohttp.org/en/stable/).

# Installation

_uapi_ requires an underlying web framework to run. If you are unsure which to pick, we recommend Starlette for a good balance of features and speed.

```{tab} Starlette

    $ pip install uapi starlette uvicorn
```

```{tab} Flask

    $ pip install uapi flask gunicorn
```

```{tab} Quart

    $ pip install uapi quart uvicorn
```

```{tab} Django

    $ pip install uapi django gunicorn
```

```{tab} Aiohttp

    $ pip install uapi aiohttp
```

# Your First Handler

Let's write a very simple _Hello World_ HTTP handler and expose it on the root path.

Before we start writing our handlers, we need something to register them with. In _uapi_, that something is an instance of an `App`.

````{tab} Starlette

```python
from uapi.starlette import App

app = App()

@app.get("/")
async def hello() -> str:
    return "hello world"
```

````

````{tab} Flask

```python
from uapi.flask import App

app = App()

@app.get("/")
def hello() -> str:
    return "hello world"
```
````

````{tab} Quart

```python
from uapi.quart import App

app = App()

@app.get("/")
async def hello() -> str:
    return "hello world"
```
````

````{tab} Django

```python
from uapi.django import App

app = App()

@app.get("/")
def hello() -> str:
    return "hello world"
```
````

````{tab} Aiohttp

```python
from uapi.aiohttp import App

app = App()

@app.get("/")
async def hello() -> str:
    return "hello world"
```
````

```{note}

_uapi_ uses type hints in certain places to minimize boilerplate code.
This doesn't mean you're required to type-check your code using a tool like Mypy, however.
We're not the Python police; you do you.

Mypy's pretty great, though.
```

Let's start serving the file.

````{tab} Starlette

Change the code to the following, and run it:
```python
from asyncio import run
from uapi.starlette import App

app = App()

@app.get("/")
async def hello() -> str:
    return "hello world"

run(app.run())
```

````

````{tab} Flask

Change the code to the following, and run it:
```python
from uapi.flask import App

app = App()

@app.get("/")
def hello() -> str:
    return "hello world"

app.run(__name__)
```
````

````{tab} Quart

Change the code to the following, and run it:
```python
from asyncio import run
from uapi.quart import App

app = App()

@app.get("/")
async def hello() -> str:
    return "hello world"

run(app.run(__name__))
```
````

```{tab} Django

Unfortunately, Django is too complex to be able to spin up a development server quickly.
Please see the Django section for information on how to integrate a _uapi_ `App` into a Django site.
```

````{tab} Aiohttp

Change the code to the following, and run it:
```python
from asyncio import run
from uapi.aiohttp import App

app = App()

@app.get("/")
async def hello() -> str:
    return "hello world"

run(app.run())
```
````

Your app is now running in development mode on localhost, port 8000.

```
$ curl 127.0.0.1:8000
hello world⏎
```
