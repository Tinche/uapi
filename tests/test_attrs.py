from json import dumps

from cattrs import unstructure
from httpx import AsyncClient

from tests.models import NestedModel


async def test_model(server):
    model = NestedModel()
    unstructured = unstructure(model)
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model", json=unstructured
        )
        assert resp.status_code == 201
        assert resp.json() == unstructured


async def test_model_wrong_content_type(server) -> None:
    """The server should refuse invalid content types, for security."""
    model = NestedModel()
    unstructured = unstructure(model)
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model",
            content=dumps(unstructured),
            headers={"content-type": "text/plain"},
        )
        assert resp.status_code == 415


async def test_model_error(server: int) -> None:
    """The server returns error on invalid data."""
    async with AsyncClient() as client:
        resp = await client.post(
            f"http://localhost:{server}/post/model", json={"a_dict": "a"}
        )
        assert resp.status_code == 400
