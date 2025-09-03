from datetime import datetime, timezone
from json import dumps

import pytest
from cattrs import unstructure
from httpx import AsyncClient

from tests.models import NestedModel


@pytest.mark.asyncio(loop_scope="session")
async def test_model(server) -> None:
    model = NestedModel()
    unstructured = unstructure(model)
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model", json=unstructured
        )
        assert resp.status_code == 201
        assert resp.json() == unstructured


@pytest.mark.asyncio(loop_scope="session")
async def test_model_wrong_content_type(server) -> None:
    """The server should refuse invalid content types, for security."""
    model = NestedModel()
    unstructured = unstructure(model)
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model",
            content=dumps(unstructured),
            headers={"content-type": "text/plain"},
        )
        assert resp.status_code == 415


@pytest.mark.asyncio(loop_scope="session")
async def test_model_error(server: int) -> None:
    """The server returns error on invalid data."""
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model", json={"a_dict": "a"}
        )
        assert resp.status_code == 400


@pytest.mark.asyncio(loop_scope="session")
async def test_patch_custom_loader_no_ct(server: int) -> None:
    """No content-type required or validated on this endpoint."""
    async with AsyncClient() as client:
        resp = await client.patch(
            f"http://localhost:{server}/custom-loader-no-ct",
            json={"simple_model": {"an_int": 2}},
        )
        assert resp.status_code == 200
        assert resp.text == "3"
        resp = await client.patch(
            f"http://localhost:{server}/custom-loader-no-ct",
            json={"simple_model": {"an_int": 2}},
            headers={"content-type": "application/vnd.uapi.v1+json"},
        )
        assert resp.status_code == 200
        assert resp.text == "3"


@pytest.mark.asyncio(loop_scope="session")
async def test_model_custom_error(server: int) -> None:
    """The server returns custom errors."""
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/custom-loader-error", json={"a_dict": "a"}
        )
        assert resp.status_code == 403
        assert resp.text == "While structuring NestedModel (1 sub-exception)"


@pytest.mark.asyncio(loop_scope="session")
async def test_attrs_union(server: int) -> None:
    """Unions of attrs classes work."""
    async with AsyncClient() as client:
        resp = await client.patch(f"http://localhost:{server}/patch/attrs")
        assert resp.status_code == 200
        assert resp.json() == {
            "a_dict": {},
            "a_list": [],
            "simple_model": {"a_float": 1.0, "a_string": "1", "an_int": 1},
        }
        resp = await client.patch(
            f"http://localhost:{server}/patch/attrs", params={"test": "1"}
        )
        assert resp.status_code == 201
        assert resp.json() == {"a_float": 1.0, "a_string": "1", "an_int": 1}


@pytest.mark.asyncio(loop_scope="session")
async def test_attrs_union_nocontent(server: int) -> None:
    """Unions of attrs classes and NoContent work."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/response-union-nocontent")
        assert resp.status_code == 200
        assert resp.json() == {"a_float": 1.0, "a_string": "1", "an_int": 1}
        resp = await client.get(
            f"http://localhost:{server}/response-union-nocontent", params={"page": "1"}
        )
        assert resp.status_code == 204
        assert resp.read() == b""


@pytest.mark.asyncio(loop_scope="session")
async def test_attrs_union_none(server: int) -> None:
    """Unions of attrs classes and None work."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/response-union-none")
        assert resp.status_code == 200
        assert resp.json() == {"a_float": 1.0, "a_string": "1", "an_int": 1}
        resp = await client.get(
            f"http://localhost:{server}/response-union-none", params={"page": "1"}
        )
        assert resp.status_code == 403
        assert resp.read() == b""


@pytest.mark.asyncio(loop_scope="session")
async def test_generic_model(server) -> None:
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/generic-model", json={"a": 1}
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "a": {"an_int": 1, "a_string": "1", "a_float": 1.0},
            "b": [],
        }


@pytest.mark.asyncio(loop_scope="session")
async def test_dictionary_models(server) -> None:
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/dictionary-models", json={"a": {}, "b": {}}
        )
        assert resp.status_code == 200
        assert resp.json() == {
            "dict_field": {
                "a": {"an_int": 1, "a_string": "1", "a_float": 1.0},
                "b": {"an_int": 1, "a_string": "1", "a_float": 1.0},
            }
        }


@pytest.mark.asyncio(loop_scope="session")
async def test_datetime_models(server) -> None:
    """datetime and date models work."""
    a_val = "2020-01-01T00:00:00+00:00"
    b_val = "2020-01-01"
    test_time = datetime.now(timezone.utc).isoformat()

    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/datetime-models",
            json={"a": a_val, "b": b_val, "c": a_val, "d": b_val},
            params={"req_query_datetime": test_time},
        )
        assert resp.status_code == 200
        assert resp.json() == {"a": a_val, "b": b_val, "c": test_time, "d": b_val}

        now = datetime.now(timezone.utc).isoformat()

        resp = await client.post(
            f"http://localhost:{server}/datetime-models",
            json={"a": a_val, "b": b_val, "c": a_val, "d": b_val},
            params={"query_datetime": now, "req_query_datetime": test_time},
        )
        assert resp.status_code == 200
        assert resp.json() == {"a": now, "b": b_val, "c": test_time, "d": b_val}
