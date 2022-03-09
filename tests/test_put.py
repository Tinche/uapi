from httpx import AsyncClient


async def test_put_cookie(server):
    async with AsyncClient() as client:
        resp = await client.put(
            f"http://localhost:{server}/put/cookie", cookies={"a_cookie": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "test"


async def test_put_cookie_optional(server):
    async with AsyncClient() as client:
        resp = await client.put(f"http://localhost:{server}/put/cookie-optional")
        assert resp.status_code == 200
        assert resp.text == "missing"
        resp = await client.put(
            f"http://localhost:{server}/put/cookie-optional",
            cookies={"A-COOKIE": "cookie"},
        )
        assert resp.status_code == 200
        assert resp.text == "cookie"
