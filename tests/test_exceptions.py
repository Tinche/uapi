"""Tests for ResponseException scenarios."""
from httpx import AsyncClient


async def test_attrs_exception(server):
    """Response exceptions work properly in all code paths."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/exc/attrs")
        assert resp.status_code == 200
        assert resp.json() == {"a_float": 1.0, "a_string": "1", "an_int": 1}
        assert resp.headers["content-type"] == "application/json"

        resp = await client.get(f"http://localhost:{server}/exc/attrs-response")
        assert resp.status_code == 200
        assert resp.json() == {"a_float": 1.0, "a_string": "1", "an_int": 1}
        assert resp.headers["content-type"] == "application/json"

        resp = await client.get(f"http://localhost:{server}/exc/attrs-none")
        assert resp.status_code == 200
        assert resp.json() == {"a_float": 1.0, "a_string": "1", "an_int": 1}
        assert resp.headers["content-type"] == "application/json"
