from pathlib import Path

from aiohttp import web
from aiohttp.web import Request, Response
from attr import define
from rich import print
from ujson import dumps

from attrsapi import Header, parameters
from attrsapi.aiohttp import SwattrsRouteTableDef, make_openapi_spec
from attrsapi.openapi import converter

routes = SwattrsRouteTableDef()


@routes.get("/")
async def hello(request: Request):
    return Response(text="Hello, world")


@define
class User:
    id: int
    username: str


@routes.get("/users/{user_id}")
async def fetch_user(user_id: int) -> User:
    return User(user_id, "test")


@routes.post("/user")
async def create_user(user: User) -> User:
    print(user)
    return user


@routes.get("/users")
async def fetch_users(page: int = 0) -> list[User]:
    print(repr(page))
    return [User(1, "test")]


@routes.get("/header")
@parameters(a_nice_header=Header("a-nice-header"))
async def show_header(a_nice_header: str) -> str:
    return a_nice_header


@routes.get("/openapi.json")
async def openapi(_) -> Response:
    res = dumps(
        converter.unstructure(s := make_openapi_spec(routes)),
        escape_forward_slashes=False,
    )
    print(s)
    print(res)
    return Response(body=res)


routes.static("/static", Path(__file__).parent / "static")

app = web.Application()
app.add_routes(routes)


def main():
    web.run_app(app)


if __name__ == "__main__":
    main()
