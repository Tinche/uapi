from httpx import AsyncClient


async def test_simple_header(server: int) -> None:
    """Headers work properly."""
    async with AsyncClient() as client:
        resp = await client.put(
            f"http://localhost:{server}/header", headers={"test-header": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "test"


async def test_missing_header(server: int) -> None:
    """Missing headers provide errors."""
    async with AsyncClient() as client:
        resp = await client.put(f"http://localhost:{server}/header")
        assert resp.status_code in (400, 500)


async def test_header_with_str_default(server: int) -> None:
    """String headers with defaults work properly."""
    async with AsyncClient() as client:
        resp = await client.put(f"http://localhost:{server}/header-string-default")
        assert resp.status_code == 200
        assert resp.text == "def"

        resp = await client.put(
            f"http://localhost:{server}/header-string-default",
            headers={"test-header": "1"},
        )
        assert resp.status_code == 200
        assert resp.text == "1"


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


async def test_header_name_override(server: int) -> None:
    """Headers can override their names."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/header-renamed")
        assert resp.status_code in (400, 500)

        resp = await client.get(
            f"http://localhost:{server}/header-renamed", headers={"test_header": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "test"
