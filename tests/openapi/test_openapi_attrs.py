"""Test the OpenAPI schema generation for attrs classes."""
from uapi.base import App
from uapi.openapi import (
    ArraySchema,
    InlineType,
    MediaType,
    OneOfSchema,
    OpenAPI,
    Reference,
    RequestBody,
    Schema,
)


def test_get_model(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/get/model"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == []
    assert op.post is None
    assert op.put is None
    assert op.get.responses["200"]
    assert op.get.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/NestedModel"
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=Schema(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


def test_get_model_status(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/get/model-status"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == []
    assert op.post is None
    assert op.put is None
    assert op.delete is None
    assert op.get.responses["201"]
    assert op.get.responses["201"].content["application/json"].schema == Reference(
        "#/components/schemas/NestedModel"
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=Schema(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


def test_post_model(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/model"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.put is None
    assert op.delete is None

    assert op.post.parameters == []
    assert op.post.requestBody == RequestBody(
        {"application/json": MediaType(Reference("#/components/schemas/NestedModel"))},
        required=True,
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=Schema(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


def test_patch_union(app: App) -> None:
    """Unions of attrs classes."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/patch/attrs"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is None
    assert op.patch is not None
    assert op.patch.responses["200"]
    assert op.patch.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/NestedModel"
    )
    assert op.patch.responses["201"].content["application/json"].schema == Reference(
        "#/components/schemas/SimpleModel"
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=Schema(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


def test_custom_loader(app: App) -> None:
    """Custom loaders advertise proper content types."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/custom-loader"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is not None
    assert op.delete is None

    assert op.put.parameters == []
    assert op.put.requestBody == RequestBody(
        {
            "application/vnd.uapi.v1+json": MediaType(
                Reference("#/components/schemas/NestedModel")
            )
        },
        required=True,
    )

    assert spec.components.schemas["NestedModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "simple_model": Reference("#/components/schemas/SimpleModel"),
            "a_list": ArraySchema(Reference("#/components/schemas/SimpleModel")),
            "a_dict": Schema(
                Schema.Type.OBJECT, additionalProperties=Schema(Schema.Type.STRING)
            ),
        },
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


def test_models_same_name(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        {
            "an_int": Schema(type=Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )
    assert spec.components.schemas["SimpleModel2"] == Schema(
        Schema.Type.OBJECT,
        {"a_different_int": Schema(type=Schema.Type.INTEGER)},
        required=["a_different_int"],
    )


def test_response_models(app: App) -> None:
    """Response models should be properly added to the spec."""
    spec: OpenAPI = app.make_openapi_spec()

    assert spec.components.schemas["ResponseModel"] == Schema(
        Schema.Type.OBJECT,
        {"a_list": ArraySchema(Reference("#/components/schemas/ResponseList"))},
        required=["a_list"],
    )
    assert spec.components.schemas["ResponseList"] == Schema(
        Schema.Type.OBJECT, {"a": Schema(type=Schema.Type.STRING)}, required=["a"]
    )


def test_response_union_none(app: App) -> None:
    """Response models of unions containing an inner None should be properly added to the spec."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/response-union-none"]
    assert op is not None
    assert op.get is not None
    assert op.post is None
    assert op.put is None
    assert op.patch is None

    assert op.get.responses["200"]
    assert op.get.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/SimpleModel"
    )
    assert op.get.responses["403"]

    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


def test_model_with_literal(app: App) -> None:
    """Models with Literal types are properly added to the spec."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/literal-model"]
    assert op is not None
    assert op.get is not None
    assert op.post is None
    assert op.put is None
    assert op.delete is None
    assert op.patch is None

    assert op.get.parameters == []
    assert op.get.requestBody == RequestBody(
        {
            "application/json": MediaType(
                Reference("#/components/schemas/ModelWithLiteral")
            )
        },
        required=True,
    )

    assert spec.components.schemas["ModelWithLiteral"] == Schema(
        Schema.Type.OBJECT,
        properties={"a": Schema(Schema.Type.STRING, enum=["a", "b", "c"])},
    )


def test_generic_model(app: App) -> None:
    """Models with Literal types are properly added to the spec."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/generic-model"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.put is None
    assert op.delete is None
    assert op.patch is None

    assert op.post.parameters == []
    assert op.post.requestBody == RequestBody(
        {
            "application/json": MediaType(
                Reference("#/components/schemas/GenericModel[int]")
            )
        },
        required=True,
    )

    assert op.post.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/GenericModel[SimpleModel]"
    )

    assert spec.components.schemas["GenericModel[int]"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "a": Schema(Schema.Type.INTEGER),
            "b": ArraySchema(InlineType(Schema.Type.INTEGER)),
        },
        required=["a"],
    )
    assert spec.components.schemas["GenericModel[SimpleModel]"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "a": Reference("#/components/schemas/SimpleModel"),
            "b": ArraySchema(Reference("#/components/schemas/SimpleModel")),
        },
        required=["a"],
    )
    assert spec.components.schemas["SimpleModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "an_int": Schema(Schema.Type.INTEGER),
            "a_string": Schema(Schema.Type.STRING),
            "a_float": Schema(Schema.Type.NUMBER, format="double"),
        },
    )


def test_generic_response_model(app: App) -> None:
    """Models from responses are collected properly."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/response-generic-model"]
    assert op is not None
    assert op.get is not None
    assert op.post is None
    assert op.put is None
    assert op.delete is None
    assert op.patch is None

    assert op.get.parameters == []
    assert op.get.requestBody is None

    assert op.get.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/ResponseGenericModel[ResponseGenericModelInner, ResponseGenericModelListInner]"
    )

    assert spec.components.schemas[
        "ResponseGenericModel[ResponseGenericModelInner, ResponseGenericModelListInner]"
    ] == Schema(
        Schema.Type.OBJECT,
        properties={
            "a": Reference("#/components/schemas/ResponseGenericModelInner"),
            "b": ArraySchema(
                Reference("#/components/schemas/ResponseGenericModelListInner")
            ),
        },
        required=["a"],
    )
    assert spec.components.schemas["ResponseGenericModelInner"] == Schema(
        Schema.Type.OBJECT,
        properties={"a": Schema(Schema.Type.INTEGER)},
        required=["a"],
    )
    assert spec.components.schemas["ResponseGenericModelListInner"] == Schema(
        Schema.Type.OBJECT,
        properties={"a": Schema(Schema.Type.INTEGER)},
        required=["a"],
    )


def test_sum_types_model(app: App) -> None:
    """Sum types are handled properly."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/sum-types-model"]
    assert op is not None
    assert op.get is not None
    assert op.post is None
    assert op.put is None
    assert op.delete is None
    assert op.patch is None

    assert op.get.parameters == []
    assert op.get.requestBody is not None
    assert op.get.requestBody.content["application/json"] == MediaType(
        Reference("#/components/schemas/SumTypesRequestModel")
    )

    assert op.get.responses["200"].content["application/json"].schema == Reference(
        "#/components/schemas/SumTypesResponseModel"
    )

    assert spec.components.schemas["SumTypesRequestModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "inner": OneOfSchema(
                [
                    Reference("#/components/schemas/SumTypesRequestInner"),
                    InlineType(Schema.Type.NULL),
                ]
            ),
            "opt_string": OneOfSchema(
                [InlineType(Schema.Type.STRING), InlineType(Schema.Type.NULL)]
            ),
            "opt_def_string": OneOfSchema(
                [InlineType(Schema.Type.STRING), InlineType(Schema.Type.NULL)]
            ),
        },
        required=["inner", "opt_string"],
    )
    assert spec.components.schemas["SumTypesRequestInner"] == Schema(
        Schema.Type.OBJECT,
        properties={"a": Schema(Schema.Type.INTEGER)},
        required=["a"],
    )
    assert spec.components.schemas["SumTypesResponseModel"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "inner": OneOfSchema(
                [
                    Reference("#/components/schemas/SumTypesResponseInner"),
                    InlineType(Schema.Type.NULL),
                ]
            )
        },
        required=["inner"],
    )
    assert spec.components.schemas["SumTypesResponseInner"] == Schema(
        Schema.Type.OBJECT,
        properties={"a": Schema(Schema.Type.INTEGER)},
        required=["a"],
    )


def test_dictionary_models(app: App) -> None:
    """Dictionary models are handled properly."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/dictionary-models"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.put is None
    assert op.delete is None
    assert op.patch is None

    assert op.post.requestBody is not None
    assert op.post.requestBody.content["application/json"].schema == Schema(
        Schema.Type.OBJECT,
        additionalProperties=Reference(ref="#/components/schemas/SimpleModel"),
    )
    assert op.post.responses["200"].content["application/json"].schema == Reference(
        ref="#/components/schemas/ModelWithDict"
    )

    assert spec.components.schemas["ModelWithDict"] == Schema(
        Schema.Type.OBJECT,
        properties={
            "dict_field": Schema(
                Schema.Type.OBJECT,
                additionalProperties=Reference(ref="#/components/schemas/SimpleModel"),
            )
        },
        required=["dict_field"],
    )
