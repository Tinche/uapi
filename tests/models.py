from typing import Generic, Literal, TypeVar

from attrs import Factory, define


@define
class SimpleModel:
    """A simple dummy model."""

    an_int: int = 1
    a_string: str = "1"
    a_float: float = 1.0


@define
class NestedModel:
    """A nested model."""

    simple_model: SimpleModel = SimpleModel()
    a_dict: dict[str, str] = {}
    a_list: list[SimpleModel] = Factory(list)


@define
class ResponseList:
    a: str


@define
class ResponseModel:
    a_list: list[ResponseList]


@define
class ModelWithLiteral:
    a: Literal["a", "b", "c"] = "a"


T = TypeVar("T")


@define
class GenericModel(Generic[T]):
    a: T
    b: list[T] = Factory(list)


@define
class ResponseGenericModel(Generic[T]):
    """Used in a response to test collection."""

    a: T


@define
class ResponseGenericModelInner:
    a: int
