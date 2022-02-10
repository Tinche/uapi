from asyncio import sleep

from httpx import AsyncClient


async def test_login_logout(secure_cookie_session_app: int):
    """Test path parameter handling."""
    username = "MyCoolUsername"
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "naughty!"

        resp = await client.post(
            f"http://localhost:{secure_cookie_session_app}/login",
            params={"username": username},
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "MyCoolUsername"

        async with AsyncClient() as new_client:
            resp = await new_client.get(
                f"http://localhost:{secure_cookie_session_app}/"
            )
            assert resp.text == "naughty!"

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "MyCoolUsername"

        resp = await client.post(f"http://localhost:{secure_cookie_session_app}/logout")
        assert resp.text == ""
        assert resp.status_code == 204
        assert not resp.cookies

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "naughty!"


async def test_session_expiry(secure_cookie_session_app: int):
    """Test path parameter handling."""
    username = "MyCoolUsername"
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "naughty!"

        resp = await client.post(
            f"http://localhost:{secure_cookie_session_app}/login",
            params={"username": username},
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "MyCoolUsername"

        await sleep(2)

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "naughty!"
