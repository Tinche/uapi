========
attrsapi
========

----

``attrsapi`` is an open source Python library for writing simple and powerful
HTTP handlers using the ``attrs`` and ``cattrs`` libraries on many of the most
popular Python web frameworks.

``attrsapi`` currently supports the following web frameworks: aiohttp, Flask, Quart, and Starlette.
Support is planned for: FastAPI, Django, Sanic.

``attrsapi`` provides a unified interface supporting:

* the GET HTTP method
* path parameters (strings, and anything loadable with cattrs)
* query parameters (strings, and anything loadable with cattrs)
