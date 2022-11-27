"""Test the OpenAPI schema generation."""
import pytest
from httpx import AsyncClient

from uapi.openapi import OpenAPI, Parameter, Response, Schema, converter

from .aiohttp import make_app as aiohttp_make_app
from .flask import make_app as flask_make_app
from .quart import make_app as quart_make_app
from .starlette import make_app as starlette_make_app


async def test_get_index(server_with_openapi: int) -> None:
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server_with_openapi}/openapi.json")
        raw = resp.json()

    spec: OpenAPI = converter.structure(raw, OpenAPI)

    op = spec.paths["/"]
    assert op is not None
    assert op.get is not None
    assert op.get.parameters == []
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]
    assert isinstance(op.get.responses["200"].content["text/plain"].schema, Schema)
    assert (
        op.get.responses["200"].content["text/plain"].schema.type == Schema.Type.STRING
    )


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_path_param(app_factory) -> None:
    app = app_factory()
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


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_query_int(app_factory) -> None:
    app = app_factory()
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


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_query_default(app_factory) -> None:
    app = app_factory()
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


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_query_unannotated(app_factory) -> None:
    app = app_factory()
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


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_query_string(app_factory) -> None:
    app = app_factory()
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


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_get_bytes(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/query-bytes"]
    assert op is not None
    assert op.get
    assert op.get.parameters == []
    assert len(op.get.responses) == 1
    assert op.get.responses["200"]
    assert op.get.responses["200"].content["application/json"].schema == Schema(
        Schema.Type.STRING, format="binary"
    )


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_post_no_body_native_response(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/no-body-native-response"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.post.parameters == []
    assert len(op.post.responses) == 1
    assert op.post.responses["200"]


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_post_no_body_no_response(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/no-body-no-response"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.post.parameters == []
    assert len(op.post.responses) == 1
    assert op.post.responses["200"]


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_post_custom_status(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/post/201"]
    assert op is not None
    assert op.get is None
    assert op.post is not None
    assert op.post.parameters == []
    assert len(op.post.responses) == 1
    assert op.post.responses["201"]


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_post_multiple_statuses(app_factory) -> None:
    app = app_factory()
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


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_put_cookie(app_factory) -> None:
    app = app_factory()
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


@pytest.mark.parametrize(
    "app_factory",
    [aiohttp_make_app, flask_make_app, quart_make_app, starlette_make_app],
    ids=["aiohttp", "flask", "quart", "starlette"],
)
def test_delete(app_factory) -> None:
    app = app_factory()
    spec: OpenAPI = app.make_openapi_spec()

    op = spec.paths["/delete/header"]
    assert op is not None
    assert op.get is None
    assert op.post is None
    assert op.put is None
    assert op.delete is not None
    assert op.delete.responses == {"204": Response("OK", {})}
