import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_index(server):
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}")
        assert resp.status_code == 200
        assert resp.text == "Hello, world"


@pytest.mark.asyncio
async def test_path_parameter(server):
    """Test path parameter handling."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/path/15")
        assert resp.status_code == 200
        assert resp.text == "16"


@pytest.mark.asyncio
async def test_query_parameter_unannotated(server):
    """Test query parameter handling for unannotated parameters."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query/unannotated", params={"query": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "testsuffix"


@pytest.mark.asyncio
async def test_query_parameter_string(server):
    """Test query parameter handling for string annotated parameters."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query/string", params={"query": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "testsuffix"


@pytest.mark.asyncio
async def test_query_parameter(server):
    """Test query parameter handling."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/query", params={"page": 10})
        assert resp.status_code == 200
        assert resp.text == "11"


async def test_query_parameter_default(server):
    """Test query parameter handling."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query-default", params={"page": 10}
        )
        assert resp.status_code == 200
        assert resp.text == "11"
        resp = await client.get(f"http://localhost:{server}/query-default")
        assert resp.status_code == 200
        assert resp.text == "1"


@pytest.mark.asyncio
async def test_query_bytes(server):
    """Test byte responses."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/query-bytes")
        assert resp.status_code == 200
        assert resp.read() == b"2"
