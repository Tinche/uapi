"""For path parameters."""
from re import compile

_angle_path_pattern = compile(r"<([a-zA-Z_]+)>")
_curly_path_pattern = compile(r"{([a-zA-Z_]+)}")


def parse_angle_path_params(path_str: str) -> list[str]:
    return _angle_path_pattern.findall(path_str)


def parse_curly_path_params(path_str: str) -> list[str]:
    return [p.split(":")[0] for p in _curly_path_pattern.findall(path_str)]


def angle_to_curly(path: str) -> str:
    return path.replace("<", "{").replace(">", "}")
