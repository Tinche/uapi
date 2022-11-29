from functools import cache
from types import MappingProxyType
from typing import Generic, Literal, Mapping, TypeAlias, TypeVar

from attrs import define, frozen

R = TypeVar("R")
S = TypeVar("S")


Headers: TypeAlias = Mapping[str, str]


@define(order=False)
class BaseResponse(Generic[S, R]):
    ret: R
    headers: Headers = MappingProxyType({})

    @classmethod
    def status_code(cls) -> int:
        return cls.__orig_bases__[0].__args__[0].__args__[0]  # type: ignore


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
