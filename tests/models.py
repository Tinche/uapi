from attr import define


@define
class SimpleModel:
    """A simple dummy model."""

    an_int: int
    a_string: str
    a_float: float
