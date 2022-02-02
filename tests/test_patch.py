from httpx import AsyncClient


async def test_patch_cookie(server):
    async with AsyncClient() as client:
        resp = await client.patch(f"http://localhost:{server}/patch/cookie")
        assert resp.status_code == 200
        assert resp.cookies["cookie"] == "my_cookie"
