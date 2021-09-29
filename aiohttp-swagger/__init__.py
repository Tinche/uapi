from pathlib import Path

from aiohttp import web
from aiohttp.web import Request, Response
from attr import define
from attrsapi import SwattrsRouteTableDef, make_openapi_spec
from ujson import dumps

routes = SwattrsRouteTableDef()


@routes.get("/")
async def hello(request: Request):
    return Response(text="Hello, world")


@define
class User:
    id: int
    username: str


@routes.get("/users/{user_id}")
async def fetch_user() -> User:
    return User(1, "test")


@routes.post("/user")
async def create_user(user: User) -> User:
    print(user)
    return user


@routes.get("/users")
async def fetch_users() -> list[User]:
    return [User(1, "test")]


@routes.get("/openapi.json")
async def openapi(_) -> Response:
    res = dumps(make_openapi_spec(routes), escape_forward_slashes=False)
    print(res)
    return Response(body=res)


routes.static("/static", Path(__file__).parent / "static")

app = web.Application()
app.add_routes(routes)


def main():
    web.run_app(app)


if __name__ == "__main__":
    main()
