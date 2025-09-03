from httpx import AsyncClient
import pytest

from uapi.status import NoContent, get_status_code


@pytest.mark.asyncio(loop_scope="session")
async def test_option_exc(server: int) -> None:
    """An option request, fulfilled by a ResponseException."""
    async with AsyncClient() as client:
        resp = await client.options(f"http://localhost:{server}/unannotated-exception")
        assert resp.status_code == get_status_code(NoContent)
