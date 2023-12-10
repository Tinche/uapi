"""Forms work with the OpenAPI schema."""
from uapi.base import App
from uapi.openapi import MediaType, Reference, RequestBody, Schema


def test_forms(app: App):
    spec = app.make_openapi_spec()

    pi = spec.paths["/form"]

    assert pi.post
    assert pi.post.parameters == []

    assert pi.post.requestBody == RequestBody(
        {
            "application/x-www-form-urlencoded": MediaType(
                schema=Reference(ref="#/components/schemas/SimpleModelNoDefaults")
            )
        }
    )
    assert spec.components.schemas["SimpleModelNoDefaults"] == Schema(
        Schema.Type.OBJECT,
        {
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
        required=["an_int", "a_string", "a_float"],
    )
