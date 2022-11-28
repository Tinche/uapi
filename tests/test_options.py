from httpx import AsyncClient

from uapi.status import NoContent, get_status_code


async def test_head_exc(server: int) -> None:
    """A head request, fulfilled by a ResponseException."""
    async with AsyncClient() as client:
        resp = await client.options(f"http://localhost:{server}/unannotated-exception")
        assert resp.status_code == get_status_code(NoContent)
