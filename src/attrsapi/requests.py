from typing import Optional

from cattr._compat import get_args, is_annotated

from . import Cookie


def get_cookie_name(t, arg_name: str) -> Optional[str]:
    if is_annotated(t):
        for arg in get_args(t)[1:]:
            if arg.__class__ is Cookie:
                return arg.name or arg_name
    return None
