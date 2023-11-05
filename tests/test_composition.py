"""Test the composition context."""
from httpx import AsyncClient


async def test_route_name(server: int):
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/comp/route-name")
        assert (await resp.aread()) == b"route_name"

        resp = await client.post(f"http://localhost:{server}/comp/route-name")
        assert (await resp.aread()) == b"route-name-post"
