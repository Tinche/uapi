from httpx import AsyncClient


async def test_simple_header(server: int) -> None:
    """Headers work properly."""
    async with AsyncClient() as client:
        resp = await client.put(
            f"http://localhost:{server}/header", headers={"test-header": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "test"


async def test_header_with_default(server: int) -> None:
    """Headers with defaults work properly."""
    async with AsyncClient() as client:
        resp = await client.put(f"http://localhost:{server}/header-default")
        assert resp.status_code == 200
        assert resp.text == "default"

        resp = await client.put(
            f"http://localhost:{server}/header-default", headers={"test-header": "1"}
        )
        assert resp.status_code == 200
        assert resp.text == "1"
