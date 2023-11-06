"""Test the composition context."""
from httpx import AsyncClient


async def test_route_name(server: int):
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/comp/route-name")
        assert (await resp.aread()) == b"route_name"

        resp = await client.get(f"http://localhost:{server}/comp/route-name-native")
        assert (await resp.aread()) == b"route_name_native"

        resp = await client.post(f"http://localhost:{server}/comp/route-name")
        assert (await resp.aread()) == b"route-name-post"

        resp = await client.post(f"http://localhost:{server}/comp/route-name-native")
        assert (await resp.aread()) == b"route-name-native-post"


async def test_request_method(server: int):
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/comp/req-method")
        assert (await resp.aread()) == b"GET"

        resp = await client.post(f"http://localhost:{server}/comp/req-method")
        assert (await resp.aread()) == b"POST"

        resp = await client.get(f"http://localhost:{server}/comp/req-method-native")
        assert (await resp.aread()) == b"GET"

        resp = await client.post(f"http://localhost:{server}/comp/req-method-native")
        assert (await resp.aread()) == b"POST"
