====
uapi
====

----

``uapi`` is an open source Python library for writing simple and powerful
HTTP handlers using the ``attrs`` and ``cattrs`` libraries on many of the most
popular Python web frameworks. ``uapi`` can also generate an OpenAPI
schema of your handlers, which can then be used by other tools
(like Swagger UI).

``uapi`` currently supports the following web frameworks: aiohttp, Flask, Quart, and Starlette.

``uapi`` provides a unified interface supporting:

* the GET, POST and PUT HTTP methods
* path parameters (strings, and anything loadable with cattrs)
* query parameters (strings, and anything loadable with cattrs)
* cookie parameters (strings), optional and required
* response types: `None`, `str`, `bytes`, or a framework-specific response type
* custom response codes (``200`` by default, customize by annotating the return type of the handler with ``tuple[Literal[201], <Result>]``)
* a handler can declare it returns multiple status codes by annotating the return type as a union of tuples of literals and result types
