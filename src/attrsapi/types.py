def is_subclass(cls, subclass) -> bool:
    """A more robust version."""
    try:
        return issubclass(cls, subclass)
    except TypeError:
        return False
