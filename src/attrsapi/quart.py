from inspect import Parameter, signature
from typing import Callable, cast

from attr import has
from cattr import structure, unstructure
from flask.app import Flask
from quart import Quart
from quart import Response as QuartResponse
from quart import request

from . import Header
from .flask import make_openapi_spec as flask_openapi_spec
from .path import parse_angle_path_params


def _generate_wrapper(
    handler: Callable,
    path: str,
    body_dumper=lambda p: QuartResponse(unstructure(p)),
    path_loader=structure,
    query_loader=structure,
):
    sig = signature(handler)
    params_meta = getattr(handler, "__attrs_api_meta__", {})
    path_params = parse_angle_path_params(path)
    lines = []
    lines.append(f"async def handler({', '.join(path_params)}) -> __attrsapi_Response:")

    res_is_present = True
    if (ret_type := sig.return_annotation) in (Parameter.empty, None):
        res_is_present = False
    else:
        try:
            res_is_native = issubclass(ret_type, QuartResponse)
        except TypeError:
            res_is_native = False

    globs = {
        "__attrsapi_inner": handler,
        "__attrsapi_request": request,
        "__attrsapi_Response": QuartResponse,
    }

    if not res_is_present:
        lines.append("  await __attrsapi_inner(")
    elif res_is_native:
        lines.append("  return await __attrsapi_inner(")
    else:
        globs["__attrsapi_dumper"] = body_dumper
        lines.append("  return __attrsapi_dumper(await __attrsapi_inner(")

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
    if not res_is_present:
        lines.append("  return __attrsapi_Response(b'')")
    elif not res_is_native:
        lines[-1] = lines[-1] + ")"

    ls = "\n".join(lines)
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
        cast(Flask, app), title, version, native_response_cl=QuartResponse
    )
