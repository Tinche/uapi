"""Test OpenAPI while composing."""
from uapi.base import App
from uapi.openapi import MediaType, OpenAPI, Response, Schema


def test_route_name_and_methods(app: App):
    """Route names and methods should be filtered out of OpenAPI schemas."""
    spec = app.make_openapi_spec()

    op = spec.paths["/comp/route-name"].get
    assert op is not None
    assert op == OpenAPI.PathItem.Operation(
        {"200": Response("OK", {"text/plain": MediaType(Schema(Schema.Type.STRING))})},
        summary="Route Name",
        operationId="route_name",
    )

    op = spec.paths["/comp/route-name"].post
    assert op is not None
    assert op == OpenAPI.PathItem.Operation(
        {"200": Response("OK", {"text/plain": MediaType(Schema(Schema.Type.STRING))})},
        summary="Route-Name-Post",
        operationId="route-name-post",
    )


def test_native_route_name_and_methods(app: App):
    """
    Route names and methods in native handlers should be filtered out of OpenAPI
    schemas.
    """
    spec = app.make_openapi_spec()

    op = spec.paths["/comp/route-name-native"].get
    assert op is not None
    assert op == OpenAPI.PathItem.Operation(
        {"200": Response("OK")},
        summary="Route Name Native",
        operationId="route_name_native",
    )

    op = spec.paths["/comp/route-name-native"].post
    assert op is not None
    assert op == OpenAPI.PathItem.Operation(
        {"200": Response("OK")},
        summary="Route-Name-Native-Post",
        operationId="route-name-native-post",
    )
