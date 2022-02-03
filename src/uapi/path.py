"""For path parameters."""
from re import compile, sub

_angle_path_pattern = compile(r"<([a-zA-Z_:]+)>")
_curly_path_pattern = compile(r"{([a-zA-Z_]+)}")
_curly_path_with_conv_pattern = compile(r"{([a-zA-Z_]+:[a-zA-Z_]+)}")


def parse_angle_path_params(path_str: str) -> list[str]:
    return [p.split(":")[-1] for p in _angle_path_pattern.findall(path_str)]


def parse_curly_path_params(path_str: str) -> list[str]:
    return [p.split(":")[0] for p in _curly_path_pattern.findall(path_str)]


def strip_path_param_prefix(path: str) -> str:
    return sub(
        _curly_path_with_conv_pattern, lambda m: f"{{{m.group(1).split(':')[1]}}}", path
    )


def angle_to_curly(path: str) -> str:
    return path.replace("<", "{").replace(">", "}")
