from asyncio import sleep

from httpx import AsyncClient


async def test_login_logout(secure_cookie_session_app: int) -> None:
    """Test logging in and out."""
    username = "MyCoolUsername"
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "not-logged-in"

        resp = await client.post(
            f"http://localhost:{secure_cookie_session_app}/login",
            params={"username": username},
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == username

        async with AsyncClient() as new_client:
            resp = await new_client.get(
                f"http://localhost:{secure_cookie_session_app}/"
            )
            assert resp.text == "not-logged-in"

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == username

        resp = await client.post(f"http://localhost:{secure_cookie_session_app}/logout")
        assert resp.text == ""
        assert resp.status_code == 204
        assert not resp.cookies

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "not-logged-in"


async def test_session_expiry(secure_cookie_session_app: int):
    """Test path parameter handling."""
    username = "MyCoolUsername"
    async with AsyncClient() as client:
        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "not-logged-in"

        resp = await client.post(
            f"http://localhost:{secure_cookie_session_app}/login",
            params={"username": username},
        )

        assert resp.status_code == 201

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == username

        await sleep(3)

        resp = await client.get(f"http://localhost:{secure_cookie_session_app}/")
        assert resp.text == "not-logged-in"
