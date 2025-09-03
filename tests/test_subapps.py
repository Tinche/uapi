from httpx import AsyncClient
import pytest


@pytest.mark.asyncio(loop_scope="session")
async def test_subapp(server):
    """Requests to subapps work."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/subapp")
        assert resp.status_code == 200
        assert resp.text == "subapp"

        resp = await client.get(f"http://localhost:{server}/subapp/subapp")
        assert resp.status_code == 200
        assert resp.text == "subapp"
