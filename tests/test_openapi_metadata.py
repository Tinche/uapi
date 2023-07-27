"""Tests for OpenAPI metadata, like summaries and descriptions."""
from collections.abc import Callable

from uapi.base import App


def test_transformers() -> None:
    """Summary transformers are correctly applied."""
    app = App()

    @app.get("/")
    def my_handler() -> None:
        """A docstring.

        Multiline.
        """
        return

    spec = app.make_openapi_spec()
    assert spec.paths["/"].get
    assert spec.paths["/"].get.summary == "My Handler"
    assert spec.paths["/"].get.description == my_handler.__doc__

    def my_summary_transformer(handler, name: str) -> str:
        return name.upper()

    def my_desc_transformer(handler: Callable, name: str) -> str:
        return (handler.__doc__ or "").split("\n")[0].strip()

    transformed_spec = app.make_openapi_spec(
        summary_transformer=my_summary_transformer,
        description_transformer=my_desc_transformer,
    )

    assert transformed_spec.paths["/"].get
    assert transformed_spec.paths["/"].get.summary == "MY_HANDLER"
    assert transformed_spec.paths["/"].get.description == "A docstring."
