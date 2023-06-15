from typing import Literal

from uapi.status import BaseResponse, R


class TooManyRequests(BaseResponse[Literal[429], R]):
    """A user-defined response class."""
