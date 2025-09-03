"""Tests for path parameters."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="session")
async def test_path_parameter(server):
    """Test path parameter handling."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/path/15")
        assert resp.status_code == 200
        assert resp.text == "16"


@pytest.mark.asyncio(loop_scope="session")
async def test_path_string(server):
    """Posting to a path URL which returns a string."""
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/path1/20")
        assert resp.status_code == 200
        assert resp.text == "22"
