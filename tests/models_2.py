"""Test models with the same name, different modules."""
from attrs import define


@define
class SimpleModel:
    """A simple dummy model, named like models.SimpleModel."""

    a_different_int: int
