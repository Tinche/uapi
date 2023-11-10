"""Tests for path parameters."""
from httpx import AsyncClient


async def test_path_parameter(server):
    """Test path parameter handling."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/path/15")
        assert resp.status_code == 200
        assert resp.text == "16"


async def test_path_string(server):
    """Posting to a path URL which returns a string."""
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/path1/20")
        assert resp.status_code == 200
        assert resp.text == "22"
