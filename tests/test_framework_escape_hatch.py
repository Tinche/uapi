"""Tests for framework escape hatches."""
from httpx import AsyncClient


async def test_framework_req(server: int) -> None:
    """Frameworks use framework requests for this endpoint."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/framework-request", headers={"test": "1"}
        )
        assert resp.status_code == 200
        assert resp.text == "framework_request1"


async def test_no_body_native_response_post(server: int) -> None:
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/no-body-native-response"
        )
        assert resp.status_code == 201
        assert resp.text == "post"


async def test_native_resp_subclass(server: int) -> None:
    """Subclasses of the native response work."""
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/framework-resp-subclass")
        assert resp.status_code == 201
        assert resp.text == "framework_resp_subclass"
