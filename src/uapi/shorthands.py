from typing import Any, Literal, Protocol, TypeVar

from .openapi import MediaType, Response, Schema
from .status import BaseResponse, NoContent, Ok

T_co = TypeVar("T_co", covariant=True)


class ResponseShorthand(Protocol[T_co]):
    @staticmethod
    def response_adapter(value: Any) -> BaseResponse:
        """Convert a value of this type into a base response."""
        ...

    @staticmethod
    def is_union_member(value: Any) -> bool:
        """Return whether the actual value of a union is this type.

        Used when handlers return unions of types.
        """
        ...

    @staticmethod
    def make_openapi_response() -> Response | None:
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
    @staticmethod
    def response_adapter(_: Any, _nc=NoContent()) -> BaseResponse:
        return _nc

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return value is None

    @staticmethod
    def make_openapi_response() -> Response:
        return Response("No content")

    @staticmethod
    def can_handle(type: Any) -> bool | Literal["check_type"]:
        return type is None


class StrShorthand(ResponseShorthand[str]):
    @staticmethod
    def response_adapter(value: Any) -> BaseResponse:
        return Ok(value, headers={"content-type": "text/plain"})

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return isinstance(value, str)

    @staticmethod
    def make_openapi_response() -> Response:
        return Response("OK", {"text/plain": MediaType(Schema(Schema.Type.STRING))})


class BytesShorthand(ResponseShorthand[bytes]):
    @staticmethod
    def response_adapter(value: Any) -> BaseResponse:
        return Ok(value, headers={"content-type": "application/octet-stream"})

    @staticmethod
    def is_union_member(value: Any) -> bool:
        return isinstance(value, bytes)

    @staticmethod
    def make_openapi_response() -> Response:
        return Response(
            "OK",
            {
                "application/octet-stream": MediaType(
                    Schema(Schema.Type.STRING, format="binary")
                )
            },
        )
