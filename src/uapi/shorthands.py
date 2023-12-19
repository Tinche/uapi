from collections.abc import Callable
from types import NoneType
from typing import Any, Literal, Protocol, TypeAlias, TypeVar, get_origin

from attrs import AttrsInstance, has
from cattrs import Converter
from incant import is_subclass
from orjson import dumps

from .openapi import MediaType, Response, SchemaBuilder
from .status import BaseResponse, NoContent, Ok

__all__ = [
    "ResponseShorthand",
    "ResponseAdapter",
    "NoneShorthand",
    "StrShorthand",
    "BytesShorthand",
]

T_co = TypeVar("T_co", covariant=True)
ResponseAdapter: TypeAlias = Callable[[Any], BaseResponse]


class ResponseShorthand(Protocol[T_co]):
    """The base protocol for response shorthands."""

    @staticmethod
    def response_adapter_factory(type: Any) -> ResponseAdapter:  # pragma: no cover
        """Produce a converter that turns a value of this type into a base response.

        :param type: The actual type being handled by the shorthand.
        """
        ...

    @staticmethod
    def is_union_member(value: Any) -> bool:  # pragma: no cover
        """Return whether the actual value of a union is this type.

        Used when handlers return unions of types.
        """
        ...

    @staticmethod
    def make_openapi_response(type: Any, builder: SchemaBuilder) -> Response | None:
        """Produce an OpenAPI response for this shorthand type.

        If this isn't overriden, no OpenAPI schema will be generated.
        """
        return None

    @staticmethod
    def can_handle(type: Any) -> bool | Literal["check_type"]:
        """Whether the shorthand can handle this type.

        Skip overriding to use an `isinstance` check and an equality check
        against the generic type parameter of the shorthand.
        """
        return "check_type"


class NoneShorthand(ResponseShorthand[None]):
    """Support for handlers returning `None`.

    The response code is set to 204, and the content type is left unset.
    """

    @staticmethod
    def response_adapter_factory(_: Any) -> ResponseAdapter:
        def response_adapter(_, _nc=NoContent()):
            return _nc

        return response_adapter

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return value is None

    @staticmethod
    def make_openapi_response(_: Any, __: SchemaBuilder) -> Response:
        return Response("No content")

    @staticmethod
    def can_handle(type: Any) -> bool | Literal["check_type"]:
        return type in (None, NoneType)


class StrShorthand(ResponseShorthand[str]):
    """Support for handlers returning `str`.

    The response code is set to 200 and the content type is set to `text/plain`.
    """

    @staticmethod
    def response_adapter_factory(type: Any) -> ResponseAdapter:
        return lambda value: Ok(value, headers={"content-type": "text/plain"})

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return isinstance(value, str)

    @staticmethod
    def make_openapi_response(_: Any, builder: SchemaBuilder) -> Response:
        return Response(
            "OK", {"text/plain": MediaType(builder.PYTHON_PRIMITIVES_TO_OPENAPI[str])}
        )


class BytesShorthand(ResponseShorthand[bytes]):
    """Support for handlers returning `bytes`.

    The response code is set to 200 and the content type is set to
    `application/octet-stream`.
    """

    @staticmethod
    def response_adapter_factory(type: Any) -> ResponseAdapter:
        return lambda value: Ok(
            value, headers={"content-type": "application/octet-stream"}
        )

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return isinstance(value, bytes)

    @staticmethod
    def make_openapi_response(_: Any, builder: SchemaBuilder) -> Response:
        return Response(
            "OK",
            {
                "application/octet-stream": MediaType(
                    builder.PYTHON_PRIMITIVES_TO_OPENAPI[bytes]
                )
            },
        )


def make_attrs_shorthand(
    converter: Converter,
) -> type[ResponseShorthand[AttrsInstance]]:
    class AttrsShorthand(ResponseShorthand[AttrsInstance]):
        """Support for handlers returning _attrs_ classes."""

        @staticmethod
        def response_adapter_factory(type: Any) -> ResponseAdapter:
            hook = converter._unstructure_func.dispatch(type)
            headers = {"content-type": "application/json"}

            def response_adapter(
                value: AttrsInstance, _h=hook, _hs=headers
            ) -> Ok[bytes]:
                return Ok(dumps(_h(value)), _hs)

            return response_adapter

        @staticmethod
        def is_union_member(value: Any) -> bool:
            return has(value.__class__) and not isinstance(value, BaseResponse)

        @staticmethod
        def make_openapi_response(type: Any, builder: SchemaBuilder) -> Response | None:
            return Response(
                "OK", {"application/json": MediaType(builder.get_schema_for_type(type))}
            )

        @staticmethod
        def can_handle(type: Any) -> bool | Literal["check_type"]:
            return has(type) and not is_subclass(get_origin(type) or type, BaseResponse)

    return AttrsShorthand


def get_shorthand_type(shorthand: type[ResponseShorthand]) -> Any:
    """Get the underlying shorthand type (ResponseShorthand[T] -> T)."""
    return shorthand.__orig_bases__[0].__args__[0]  # type: ignore


def can_shorthand_handle(type: Any, shorthand: type[ResponseShorthand]) -> bool:
    res = shorthand.can_handle(type)
    return res is True or (
        res == "check_type"
        and ((st := get_shorthand_type(shorthand)) is type or is_subclass(type, st))
    )
