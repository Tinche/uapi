from httpx import AsyncClient
import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_patch_cookie(server):
    """Patch requests work."""
    async with AsyncClient() as client:
        resp = await client.patch(f"http://localhost:{server}/patch/cookie")
        assert resp.status_code == 200
        assert resp.cookies["cookie"] == "my_cookie"
