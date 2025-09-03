import pytest
from httpx import AsyncClient


@pytest.mark.asyncio(loop_scope="session")
async def test_hello(server):
    """The hello handler should work, to show chaining of @route decorators."""
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/")
        assert resp.status_code == 200


@pytest.mark.asyncio(loop_scope="session")
async def test_no_body_no_response_post(server: int) -> None:
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/post/no-body-no-response")
        assert resp.status_code == 204
        assert resp.read() == b""


@pytest.mark.asyncio(loop_scope="session")
async def test_201(server):
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/post/201")
        assert resp.status_code == 201
        assert resp.text == "test"


@pytest.mark.asyncio(loop_scope="session")
async def test_multiple(server):
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/post/multiple")
        assert resp.status_code == 201
        assert resp.read() == b""
