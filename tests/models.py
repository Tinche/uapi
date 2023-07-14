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
    a_dict: dict[str, str] = Factory(dict)
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
U = TypeVar("U")


@define
class GenericModel(Generic[T]):
    a: T
    b: list[T] = Factory(list)


@define
class ResponseGenericModel(Generic[T, U]):
    """Used in a response to test collection."""

    a: T
    b: list[U] = Factory(list)


@define
class ResponseGenericModelInner:
    a: int


@define
class ResponseGenericModelListInner:
    a: int


@define
class SumTypesRequestModel:
    @define
    class SumTypesRequestInner:
        a: int

    inner: SumTypesRequestInner | None
    opt_string: str | None
    opt_def_string: str | None = None


@define
class SumTypesResponseModel:
    @define
    class SumTypesResponseInner:
        a: int

    inner: SumTypesResponseInner | None


@define
class ModelWithDict:
    dict_field: dict[str, SimpleModel]
