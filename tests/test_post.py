from json import dumps

from cattrs import unstructure
from httpx import AsyncClient

from tests.models import NestedModel


async def test_no_body_native_response_post(server):
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/no-body-native-response"
        )
        assert resp.status_code == 201
        assert resp.text == "post"


async def test_no_body_no_response_post(server):
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/post/no-body-no-response")
        assert resp.status_code == 200


async def test_201(server):
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/post/201")
        assert resp.status_code == 201
        assert resp.text == "test"


async def test_multiple(server):
    async with AsyncClient() as client:
        resp = await client.post(f"http://localhost:{server}/post/multiple")
        assert resp.status_code == 201
        assert resp.read() == b""


async def test_model(server):
    model = NestedModel()
    unstructured = unstructure(model)
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model", json=unstructured
        )
        assert resp.status_code == 201
        assert resp.json() == unstructured


async def test_model_wrong_content_type(server):
    """The server should refuse invalid content types, for security."""
    model = NestedModel()
    unstructured = unstructure(model)
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model",
            content=dumps(unstructured),
            headers={"content-type": "text/plain"},
        )
        assert resp.status_code == 400
