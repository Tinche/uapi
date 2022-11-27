from httpx import AsyncClient


async def test_patch_cookie(server):
    async with AsyncClient() as client:
        resp = await client.patch(f"http://localhost:{server}/patch/cookie")
        assert resp.status_code == 200
        assert resp.cookies["cookie"] == "my_cookie"


async def test_patch_custom_loader_no_ct(server: int) -> None:
    """No content-type required or validated on this endpoint."""
    async with AsyncClient() as client:
        resp = await client.patch(
            f"http://localhost:{server}/custom-loader-no-ct",
            json={"simple_model": {"an_int": 2}},
        )
        assert resp.status_code == 200
        assert resp.text == "3"
        resp = await client.patch(
            f"http://localhost:{server}/custom-loader-no-ct",
            json={"simple_model": {"an_int": 2}},
            headers={"content-type": "application/vnd.uapi.v1+json"},
        )
        assert resp.status_code == 200
        assert resp.text == "3"
