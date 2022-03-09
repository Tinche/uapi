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
