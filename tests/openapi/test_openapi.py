"""Test the OpenAPI schema generation."""
from httpx import AsyncClient

from uapi.base import App
from uapi.openapi import OpenAPI, Parameter, Response, Schema, converter


async def test_get_index(server_with_openapi: int) -> None:
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server_with_openapi}/openapi.json")
        raw = resp.json()

    spec: OpenAPI = converter.structure(raw, OpenAPI)

    op = spec.paths["/"]
    assert op is not None
    assert op.get is not None
    assert op.get.summary == "Hello"
    assert op.get.description == "To be used as a description."
    assert op.get.operationId == "hello"
    assert op.get.parameters == []
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]
    assert isinstance(op.get.responses["200"].content["text/plain"].schema, Schema)
    assert (
        op.get.responses["200"].content["text/plain"].schema.type == Schema.Type.STRING
    )

    assert op.post is not None
    assert op.post.summary == "Hello-Post"
    assert op.post.operationId == "hello-post"
    assert op.get.description == "To be used as a description."


def test_get_path_param(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/path/{path_id}"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == [
        Parameter(
            name="path_id",
            kind=Parameter.Kind.PATH,
            required=True,
            schema=Schema(Schema.Type.INTEGER),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]
    assert op.get.responses["200"].content == {}

    assert op.get.description is None


def test_get_query_int(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == [
        Parameter(
            name="page",
            kind=Parameter.Kind.QUERY,
            required=True,
            schema=Schema(Schema.Type.INTEGER),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_query_default(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query-default"]
    assert op is not None
    assert op.get
    assert op.get.parameters == [
        Parameter(
            name="page",
            kind=Parameter.Kind.QUERY,
            required=False,
            schema=Schema(Schema.Type.INTEGER),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_query_unannotated(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query/unannotated"]
    assert op is not None
    assert op.get
    assert op.get.parameters == [
        Parameter(
            name="query",
            kind=Parameter.Kind.QUERY,
            required=True,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_query_string(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query/string"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == [
        Parameter(
            name="query",
            kind=Parameter.Kind.QUERY,
            required=True,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_get_bytes(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/response-bytes"]
    assert op is not None
    assert op.get
    assert op.get.parameters == []
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]
    assert op.get.responses["200"].content["application/octet-stream"].schema == Schema(
        Schema.Type.STRING, format="binary"
    )


def test_post_no_body_native_response(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/no-body-native-response"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.post.parameters == []
    assert len(op.post.responses) == 1
    assert op.post.responses["200"]


def test_post_no_body_no_response(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/no-body-no-response"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.post.parameters == []
    assert len(op.post.responses) == 1
    assert op.post.responses["204"]


def test_post_custom_status(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/201"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.post.parameters == []
    assert len(op.post.responses) == 1
    assert op.post.responses["201"]


def test_post_multiple_statuses(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/multiple"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.post.parameters == []
    assert len(op.post.responses) == 2
    assert op.post.responses["200"]
    schema = op.post.responses["200"].content["text/plain"].schema
    assert isinstance(schema, Schema)
    assert schema.type == Schema.Type.STRING
    assert op.post.responses["201"]
    assert not op.post.responses["201"].content


def test_put_cookie(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/put/cookie"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is not None
    assert op.put.parameters == [
        Parameter(
            "a_cookie",
            Parameter.Kind.COOKIE,
            required=True,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert op.put.responses["200"]
    schema = op.put.responses["200"].content["text/plain"].schema
    assert isinstance(schema, Schema)
    assert schema.type == Schema.Type.STRING


def test_delete(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/delete/header"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is None
    assert op.delete is not None
    assert op.delete.responses == {"204": Response("No content", {})}


def test_ignore_framework_request(app: App) -> None:
    """Framework request params are ignored."""
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/framework-request"]
    assert op is not None
    assert op.get is not None
    assert op.post is None
    assert op.put is None
    assert op.patch is None
    assert op.delete is None

    assert op.get.parameters == []


def test_get_injection(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/injection"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == [
        Parameter(
            name="header-for-injection",
            kind=Parameter.Kind.HEADER,
            required=True,
            schema=Schema(Schema.Type.STRING),
        )
    ]
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]


def test_excluded(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec(exclude={"excluded"})

    assert "/excluded" not in spec.paths


def test_tags(app: App) -> None:
    """Tags are properly generated."""
    spec: OpenAPI = app.make_openapi_spec()

    tagged_routes = [
        ("/response-bytes", "get"),
        ("/query/unannotated", "get"),
        ("/query/string", "get"),
        ("/query", "get"),
        ("/query-default", "get"),
    ]

    for path, path_item in spec.paths.items():
        for method in ("get", "post", "put", "delete", "patch"):
            if getattr(path_item, method) is not None:
                if (path, method) in tagged_routes:
                    assert ["query"] == getattr(path_item, method).tags
                else:
                    assert not getattr(path_item, method).tags


def test_user_response_class(app: App) -> None:
    spec: OpenAPI = app.make_openapi_spec(exclude={"excluded"})

    pathitem = spec.paths["/throttled"]
    assert pathitem.get is not None

    assert "429" in pathitem.get.responses
    assert "200" in pathitem.get.responses
