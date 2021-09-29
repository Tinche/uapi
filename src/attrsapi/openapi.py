from attr import fields

PYTHON_PRIMITIVES_TO_OPENAPI = {
    str: ("string", None),
    int: ("integer", None),
    bool: ("boolean", None),
    float: ("number", "double"),
}


def build_attrs_schema(type: type) -> dict:
    properties = {}
    for a in fields(type):
        attr_prop = {}
        if a.type in PYTHON_PRIMITIVES_TO_OPENAPI:
            t, format = PYTHON_PRIMITIVES_TO_OPENAPI[a.type]
            attr_prop["type"] = t
            if format is not None:
                attr_prop["format"] = format
        properties[a.name] = attr_prop

    return {"type": "object", "properties": properties}
