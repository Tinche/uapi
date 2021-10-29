========
attrsapi
========

----

``attrsapi`` is an open source Python library for writing simple and powerful
HTTP handlers using the ``attrs`` and ``cattrs`` libraries on many of the most
popular Python web frameworks. ``attrsapi`` can also generate an OpenAPI
schema of your handlers, which can then be used by other tools
(like Swagger UI).

``attrsapi`` currently supports the following web frameworks: aiohttp, Flask, Quart, and Starlette.
Support is planned for: FastAPI, Django, Sanic.

``attrsapi`` provides a unified interface supporting:

* the GET and POST HTTP methods
* path parameters (strings, and anything loadable with cattrs)
* query parameters (strings, and anything loadable with cattrs)
