"""OpenAPI works with shorthands."""
from datetime import datetime, timezone

from uapi.openapi import MediaType, Response, Schema
from uapi.quart import App

from ..test_shorthands import DatetimeShorthand


def test_no_openapi():
    """Shorthands without OpenAPI support work."""
    app = App()

    @app.get("/")
    async def datetime_handler() -> datetime:
        return datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)

    app.add_response_shorthand(DatetimeShorthand)

    spec = app.make_openapi_spec()

    assert spec.paths["/"]
    assert spec.paths["/"].get is not None
    assert spec.paths["/"].get.responses == {}


def test_has_openapi():
    """Shorthands without OpenAPI support work."""

    class OpenAPIDateTime(DatetimeShorthand):
        @staticmethod
        def make_openapi_response() -> Response | None:
            return Response(
                "DESC",
                {"test": MediaType(Schema(Schema.Type.STRING, format="datetime"))},
            )

    app = App()

    @app.get("/")
    async def datetime_handler() -> datetime:
        return datetime(2000, 1, 1, 0, 0, 0, 0, tzinfo=timezone.utc)

    app.add_response_shorthand(OpenAPIDateTime)

    spec = app.make_openapi_spec()

    assert spec.paths["/"]
    assert spec.paths["/"].get is not None
    assert spec.paths["/"].get.responses == {
        "200": Response(
            "DESC", {"test": MediaType(Schema(Schema.Type.STRING, format="datetime"))}
        )
    }
