from httpx import AsyncClient

from uapi.status import Forbidden, get_status_code


async def test_head_exc(server):
    """A head request, fulfilled by a ResponseException."""
    async with AsyncClient() as client:
        resp = await client.head(f"http://localhost:{server}/head/exc")
        assert resp.status_code == get_status_code(Forbidden)
