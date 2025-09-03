"""Status code classes for return values."""

from functools import cache
from typing import Generic, Literal, TypeAlias, TypeVar

from attrs import Factory, define, frozen

__all__ = [
    "BadRequest",
    "BaseResponse",
    "Created",
    "Forbidden",
    "Found",
    "InternalServerError",
    "NoContent",
    "NotFound",
    "Ok",
    "R",
    "SeeOther",
]

R = TypeVar("R")
S = TypeVar("S")


Headers: TypeAlias = dict[str, str]


@define(order=False)
class BaseResponse(Generic[S, R]):
    ret: R
    headers: Headers = Factory(dict)

    @classmethod
    def status_code(cls) -> int:
        return cls.__orig_bases__[0].__args__[0].__args__[0]  # type: ignore


@define
class ResponseException(Exception):
    """An exception that is converted into an HTTP response."""

    response: BaseResponse


@cache
def get_status_code(resp: type[BaseResponse]) -> int:
    return resp.status_code()


@define
class Ok(BaseResponse[Literal[200], R]):
    pass


@define
class Created(BaseResponse[Literal[201], R]):
    pass


@frozen
class NoContent(BaseResponse[Literal[204], None]):
    ret: None = None

    @classmethod
    def status_code(cls) -> int:
        return 204


@define
class Found(BaseResponse[Literal[302], R]):
    pass


@define
class SeeOther(BaseResponse[Literal[303], R]):
    pass


@define
class BadRequest(BaseResponse[Literal[400], R]):
    pass


@define
class Forbidden(BaseResponse[Literal[403], R]):
    pass


@define
class NotFound(BaseResponse[Literal[404], R]):
    pass


@define
class InternalServerError(BaseResponse[Literal[500], R]):
    pass
