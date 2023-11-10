from httpx import AsyncClient


async def test_put_custom_loader(server: int) -> None:
    async with AsyncClient() as client:
        resp = await client.put(
            f"http://localhost:{server}/custom-loader",
            json={"simple_model": {"an_int": 2}},
        )
        assert resp.status_code == 415
        assert (
            resp.text == "invalid content type (expected application/vnd.uapi.v1+json)"
        )
        resp = await client.put(
            f"http://localhost:{server}/custom-loader",
            json={"simple_model": {"an_int": 2}},
            headers={"content-type": "application/vnd.uapi.v1+json"},
        )
        assert resp.status_code == 200
        assert resp.text == "2"
