from inspect import Parameter, signature
from typing import Any, Callable, Union, cast

from attr import has
from cattr import structure, unstructure
from flask.app import Flask
from quart import Quart
from quart import Response as FrameworkResponse
from quart import request

from . import Header
from .flask import make_openapi_spec as flask_openapi_spec
from .path import parse_angle_path_params
from .requests import get_cookie_name
from .responses import get_status_code_results, returns_status_code
from .types import is_subclass

try:
    from functools import partial

    from ujson import dumps as usjon_dumps

    dumps: Callable[[Any], Union[bytes, str]] = partial(
        usjon_dumps, ensure_ascii=False, escape_forward_slashes=False
    )
except ImportError:
    from json import dumps


def _generate_wrapper(
    handler: Callable,
    path: str,
    body_dumper=lambda v: dumps(unstructure(v)),
    path_loader=structure,
    query_loader=structure,
):
    sig = signature(handler)
    params_meta: dict[str, Header] = getattr(handler, "__attrs_api_meta__", {})
    path_params = parse_angle_path_params(path)
    lines = []
    post_lines = []
    lines.append(f"async def handler({', '.join(path_params)}) -> __attrsapi_Response:")

    globs = {
        "__attrsapi_inner": handler,
        "__attrsapi_request": request,
        "__attrsapi_Response": FrameworkResponse,
    }

    if (ret_type := sig.return_annotation) in (None, Parameter.empty):
        lines.append("  __attrsapi_sc = 200")
        lines.append("  await __attrsapi_inner(")
        post_lines.append(
            "  return __attrsapi_Response(response=b'', status=__attrsapi_sc)"
        )
    else:
        if is_subclass(ret_type, FrameworkResponse):
            # The response is native.
            lines.append("  return await __attrsapi_inner(")
        else:
            sc_results = get_status_code_results(ret_type)
            if returns_status_code(ret_type):
                lines.append(
                    "  __attrsapi_sc, __attrsapi_res = await __attrsapi_inner("
                )
            else:
                lines.append("  __attrsapi_sc = 200")
                lines.append("  __attrsapi_res = await __attrsapi_inner(")

            resp_processors = {}
            for sc, rt in sc_results:
                if rt in (bytes, str):
                    resp_processors[sc] = "__attrsapi_res", lambda r: r
                elif rt is None:
                    resp_processors[sc] = "b''", lambda r: b""
                elif has(rt):
                    resp_processors[sc] = (
                        "__attrsapi_dumper(__attrsapi_res)",
                        body_dumper,
                    )
                    globs["__attrsapi_dumper"] = body_dumper
                else:
                    raise Exception(f"Cannot handle response type {ret_type}/{rt}")

            if len({v[0] for v in resp_processors.values()}) == 1:
                body_expr = next(iter(resp_processors.values()))[0]
            else:
                body_expr = "(__attrsapi_rp[__attrsapi_sc])(__attrsapi_res)"
                globs["__attrsapi_rp"] = {k: v[1] for k, v in resp_processors.items()}

            post_lines.append(
                f"  return __attrsapi_Response(response={body_expr}, status=__attrsapi_sc)"
            )

    for arg, arg_param in sig.parameters.items():
        if arg in path_params:
            arg_annotation = sig.parameters[arg].annotation
            if arg_annotation in (Parameter.empty, str):
                lines.append(f"    {arg},")
            else:
                lines.append(
                    f"    __attrsapi_path_loader({arg}, __attrsapi_{arg}_type),"
                )
                globs["__attrsapi_path_loader"] = path_loader
                globs[f"__attrsapi_{arg}_type"] = arg_annotation
        elif arg_meta := params_meta.get(arg):
            if isinstance(arg_meta, Header):
                # A header param.
                lines.append(f"    request.headers['{arg_meta.name}'],")
        elif (arg_type := arg_param.annotation) is not Parameter.empty and has(
            arg_type
        ):
            # defaulting to body
            pass
        elif cookie_name := get_cookie_name(arg_type, arg):
            if arg_param.default is Parameter.empty:
                lines.append(f"    __attrsapi_request.cookies['{cookie_name}'],")
            else:
                lines.append(
                    f"    __attrsapi_request.cookies.get('{cookie_name}', __{arg}_default),"
                )
                globs[f"__{arg}_default"] = arg_param.default
        else:
            # defaulting to query
            if arg_param.default is Parameter.empty:
                expr = f"__attrsapi_request.args['{arg}']"
            else:
                expr = f"__attrsapi_request.args.get('{arg}', __attrsapi_{arg}_default)"
                globs[f"__attrsapi_{arg}_default"] = arg_param.default

            if (
                arg_param.annotation is not str
                and arg_param.annotation is not Parameter.empty
            ):
                expr = f"__attrsapi_query_loader({expr}, __attrsapi_{arg}_type)"
                globs["__attrsapi_query_loader"] = query_loader
                globs[f"__attrsapi_{arg}_type"] = arg_param.annotation
            lines.append(f"    {expr},")

    lines.append("  )")

    ls = "\n".join(lines + post_lines)
    eval(compile(ls, "", "exec"), globs)

    fn = globs["handler"]

    return fn


def route(path: str, app: Quart, methods=["GET"]) -> Callable[[Callable], Callable]:
    def inner(handler: Callable) -> Callable:
        adapted = _generate_wrapper(handler, path)
        adapted.__attrsapi_handler__ = handler
        app.route(path, methods=methods, endpoint=handler.__name__)(adapted)
        return handler

    return inner


def make_openapi_spec(app: Quart, title: str = "Server", version: str = "1.0"):
    return flask_openapi_spec(
        cast(Flask, app), title, version, native_response_cl=FrameworkResponse
    )
