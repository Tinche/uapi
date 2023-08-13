"""Tests for OpenAPI metadata, like summaries and descriptions."""
from collections.abc import Callable

from uapi.aiohttp import App
from uapi.openapi import OpenAPI, converter


def test_transformers() -> None:
    """Transformers are correctly applied."""
    app = App()

    @app.get("/")
    def my_handler() -> None:
        """A docstring.

        Multiline.
        """
        return

    @app.incant.register_by_name
    def test(q: int) -> int:
        return q

    # This handler uses dependency injection so will get wrapped
    # by incant.
    @app.post("/")
    def handler_with_injection(test: int) -> None:
        """A simple docstring."""
        return

    spec = app.make_openapi_spec()
    assert spec.paths["/"].get
    assert spec.paths["/"].get.summary == "My Handler"
    assert spec.paths["/"].get.description == my_handler.__doc__

    def my_summary_transformer(handler, name: str) -> str:
        return name.upper()

    def my_desc_transformer(handler: Callable, name: str) -> str:
        """Return the first line of the docstring."""
        return (handler.__doc__ or "").split("\n")[0].strip()

    app.serve_openapi(
        summary_transformer=my_summary_transformer,
        description_transformer=my_desc_transformer,
    )

    handler = app._route_map[("GET", "/openapi.json")]

    transformed_spec = converter.loads(handler[0]().ret, OpenAPI)

    assert transformed_spec.paths["/"].get
    assert transformed_spec.paths["/"].get.summary == "MY_HANDLER"
    assert transformed_spec.paths["/"].get.description == "A docstring."

    assert transformed_spec.paths["/"].post
    assert transformed_spec.paths["/"].post.summary == "HANDLER_WITH_INJECTION"
    assert transformed_spec.paths["/"].post.description == "A simple docstring."
