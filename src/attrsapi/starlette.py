from inspect import Parameter, signature
from typing import Callable

from attr import has
from cattr import structure, unstructure
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse
from starlette.routing import Route

from . import Header
from .aiohttp import parse_path_params


def _generate_wrapper(
    handler: callable,
    path: str,
    body_dumper=lambda p: StarletteResponse(unstructure(p)),
    path_loader=structure,
    query_loader=structure,
):
    sig = signature(handler)
    params_meta = getattr(handler, "__attrs_api_meta__", {})
    path_params = parse_path_params(path)
    lines = []
    lines.append("async def handler(request: Request):")

    try:
        res_is_native = (
            (ret_type := sig.return_annotation)
            and ret_type is not Parameter.empty
            and issubclass(ret_type, StarletteResponse)
        )
    except TypeError:
        res_is_native = False

    globs = {"__attrsapi_inner": handler, "Request": StarletteRequest}

    if res_is_native:
        lines.append("  return await __attrsapi_inner(")
    else:
        globs["__attrsapi_dumper"] = body_dumper
        lines.append("  return __attrsapi_dumper(await __attrsapi_inner(")

    for arg, arg_param in sig.parameters.items():
        if arg in path_params:
            arg_annotation = sig.parameters[arg].annotation
            if arg_annotation in (Parameter.empty, str):
                lines.append(f"    request.path_params['{arg}'],")
            else:
                lines.append(
                    f"    __attrsapi_path_loader(request.path_params['{arg}'], __attrsapi_{arg}_type),"
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
                expr = f"request.query_params['{arg}']"
            else:
                expr = f"request.query_params.get('{arg}', __attrsapi_{arg}_default)"
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
    if not res_is_native:
        lines[-1] = lines[-1] + ")"

    ls = "\n".join(lines)
    eval(compile(ls, "", "exec"), globs)

    fn = globs["handler"]

    return fn


def route(path: str, handler: Callable) -> Route:
    adapted = _generate_wrapper(handler, path)
    adapted.__attrsapi_handler__ = handler

    return Route(path, adapted)
