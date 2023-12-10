"""Tests for forms."""
from httpx import AsyncClient


async def test_simple_form(server):
    """Simplest of forms work."""
    async with AsyncClient() as client:
        # content type will be automatically set to
        # "application/x-www-form-urlencoded" by httpx
        resp = await client.post(
            f"http://localhost:{server}/form",
            data={"an_int": 2, "a_string": "2", "a_float": 2.0},
        )
        assert resp.status_code == 200
        assert resp.read() == b"2"


async def test_wrong_content_type(server):
    """Wrong content types are rejected."""
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/form",
            data={"an_int": 2, "a_string": "2", "a_float": 2.0},
            headers={"content-type": "application/json"},
        )

        # All frameworks currently silently supply an empty form dictionary,
        # which makes the structuring fail.
        assert resp.status_code == 400


async def test_validation_failure(server):
    """Validation failures are handled properly."""
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/form", data={"an_int": "test"}
        )
    assert resp.status_code == 400
