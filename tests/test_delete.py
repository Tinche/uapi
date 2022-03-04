from httpx import AsyncClient


async def test_delete_response_header(server):
    async with AsyncClient() as client:
        resp = await client.delete(f"http://localhost:{server}/delete/header")
        assert resp.status_code == 204
        assert resp.headers["response"] == "test"
