import inspect
import types
import typing
from pathlib import Path

TYPE_MAP = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
    bytes: "string",
    type(None): "nil",
}

def lua_type(annotation) -> str:
    if annotation is inspect.Parameter.empty or annotation is None:
        return "any"
    origin = typing.get_origin(annotation)

    if origin is typing.Union or isinstance(annotation, types.UnionType):
        args = typing.get_args(annotation)
        parts = [lua_type(a) for a in args if a is not type(None)]
        result = "|".join(dict.fromkeys(parts))
        if type(None) in args:
            result += "|nil"
        return result

    if origin in (list, set, frozenset):
        args = typing.get_args(annotation)
        return f"{lua_type(args[0])}[]" if args else "table"

    if origin is tuple:
        return "table"

    if origin is dict:
        args = typing.get_args(annotation)
        if len(args) == 2:
            return f"table<{lua_type(args[0])}, {lua_type(args[1])}>"
        return "table"

    if annotation in TYPE_MAP:
        return TYPE_MAP[annotation]

    if inspect.isclass(annotation):
        return annotation.__name__

    return str(annotation).replace("typing.", "")

def generate_class_stub(cls, lines: list[str], is_global: bool = False) -> None:
    fields: list[str] = []
    methods: list[str] = []

    for name, member in inspect.getmembers(cls):
        if name.startswith("_") and name not in ("__init__",):
            continue
        if name == "__init__":
            continue

        if isinstance(member, property):
            ret_type = "any"
            if member.fget:
                hints = typing.get_type_hints(member.fget)
                ret_type = lua_type(hints.get("return"))
            fields.append(f"---@field {name} {ret_type}")
            continue

        if inspect.isfunction(member):
            m_lines = []
            sig = inspect.signature(member)
            params = list(sig.parameters.values())[1:]
            arg_names = []
            for p in params:
                if p.kind is p.VAR_POSITIONAL:
                    m_lines.append(f"---@vararg {lua_type(p.annotation)}")
                    continue
                if p.kind is p.VAR_KEYWORD:
                    continue
                arg_names.append(p.name)
                m_lines.append(f"---@param {p.name} {lua_type(p.annotation)}")

            ret = sig.return_annotation
            if ret not in (inspect.Signature.empty, None):
                m_lines.append(f"---@return {lua_type(ret)}")

            m_lines.append(f"function {cls.__name__}.{name}({', '.join(arg_names)}) end")
            m_lines.append("")
            methods.append("\n".join(m_lines))

    lines.append(f"---@class {cls.__name__}")
    for f in fields:
        lines.append(f)
    prefix = "" if is_global else "local "
    lines.append(f"{prefix}{cls.__name__} = {{}}")
    lines.append("")
    lines.extend(methods)

    for name, member in inspect.getmembers(cls, inspect.isclass):
        if member.__qualname__.startswith(cls.__qualname__ + "."):
            generate_class_stub(member, lines)

def write_stub(cls, out_path: str) -> None:
    lines: list[str] = ["---@meta", ""]
    generate_class_stub(cls, lines, is_global=True)
    path = (Path("output") / out_path)
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")

if __name__ == "__main__":
    from desktop.mods_manager import ModAPI
    write_stub(ModAPI, "stubs/mod_api.lua")
