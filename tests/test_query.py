import pytest
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="session")
async def test_query_post(server: int):
    """Test query params in posts."""
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/query-post", params={"page": "2"}
        )
        assert resp.status_code == 200
        assert resp.read() == b"3"


@pytest.mark.asyncio(loop_scope="session")
async def test_query_string_list(server: int):
    """Multiple query params can be gathered into lists."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query-list", params={"param": ["1", "2", "3"]}
        )
        assert resp.status_code == 200
        assert resp.read() == b"6"

        resp = await client.get(
            f"http://localhost:{server}/query-list-def",
            params={"param": ["1", "2", "3"]},
        )
        assert resp.status_code == 200
        assert resp.read() == b"6"

        resp = await client.get(f"http://localhost:{server}/query-list-def")
        assert resp.status_code == 200
        assert resp.read() == b"3"


@pytest.mark.asyncio(loop_scope="session")
async def test_query_nonstring_list(server: int):
    """Multiple non-string query params can be gathered into lists."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query-list-nonstring",
            params={"param": ["1", "2", "3"]},
        )
        assert resp.status_code == 200
        assert resp.read() == b"6"


@pytest.mark.asyncio(loop_scope="session")
async def test_query_seq(server: int):
    """Multiple query params can be gathered into sequences."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query-seq", params={"param": ["1", "2", "3"]}
        )
        assert resp.status_code == 200
        assert resp.read() == b"6"
