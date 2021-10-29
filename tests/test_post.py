import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_no_body_native_response_post(server):
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/no-body-native-response"
        )
        assert resp.status_code == 201
        assert resp.text == "post"


@pytest.mark.asyncio
async def test_no_body_no_response_post(server):
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/post/no-body-no-response")
        assert resp.status_code == 200
