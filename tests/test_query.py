from httpx import AsyncClient
import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_query_post(server):
    """Test query params in posts."""
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/query-post", params={"page": "2"}
        )
        assert resp.status_code == 200
        assert resp.read() == b"3"
