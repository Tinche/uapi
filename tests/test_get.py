from httpx import AsyncClient


async def test_index(server):
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}")
        assert resp.status_code == 200
        assert resp.text == "Hello, world"
        assert resp.headers["content-type"] == "text/plain"


async def test_query_parameter_unannotated(server):
    """Test query parameter handling for unannotated parameters."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query/unannotated", params={"query": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "testsuffix"


async def test_query_parameter_string(server):
    """Test query parameter handling for string annotated parameters."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query/string", params={"query": "test"}
        )
        assert resp.status_code == 200
        assert resp.text == "testsuffix"


async def test_query_parameter(server):
    """Test query parameter handling."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/query", params={"page": 10})
        assert resp.status_code == 200
        assert resp.text == "11"


async def test_query_parameter_default(server):
    """Test query parameter handling."""
    async with AsyncClient() as client:
        resp = await client.get(
            f"http://localhost:{server}/query-default", params={"page": 10}
        )
        assert resp.status_code == 200
        assert resp.text == "11"
        resp = await client.get(f"http://localhost:{server}/query-default")
        assert resp.status_code == 200
        assert resp.text == "1"


async def test_response_bytes(server):
    """Test byte responses."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/response-bytes")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/octet-stream"
        assert resp.read() == b"2"


async def test_response_model(server):
    """Test models in the response."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/get/model")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/json"
        assert (
            resp.read()
            == b'{"simple_model":{"an_int":1,"a_string":"1","a_float":1.0},"a_dict":{},"a_list":[]}'
        )


async def test_response_model_custom_status(server):
    """Test models in the response."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/get/model-status")
        assert resp.status_code == 201
        assert resp.headers["content-type"] == "application/json"
        assert resp.headers["test"] == "test"
        assert (
            resp.read()
            == b'{"simple_model":{"an_int":1,"a_string":"1","a_float":1.0},"a_dict":{},"a_list":[]}'
        )


async def test_user_response_class(server):
    """Test user response classes."""
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{server}/throttled")
        assert resp.status_code == 429
        assert resp.headers["content-length"] == "0"
