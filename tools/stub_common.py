import ast
from pathlib import Path

import app.config as config
from tools import PROJECT_DIR

DESKTOP_DIR = config.APP_DIR / "desktop"
SOURCES = [DESKTOP_DIR / "mod_api.py", DESKTOP_DIR / "mods_manager.py", DESKTOP_DIR / "input_events.py"]
OUT_PATH: Path = PROJECT_DIR / "tools" / "output" / "stubs"
ROOT = "ModAPI"

def collect_classes() -> dict[str, ast.ClassDef]:
    """Top-level classes from SOURCES by name (nested classes stay inside their parent)."""
    classes: dict[str, ast.ClassDef] = {}
    for path in SOURCES:
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef):
                classes[node.name] = node
    return classes

def public_methods(cls: ast.ClassDef) -> list[ast.FunctionDef]:
    return [n for n in cls.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]

def public_fields(cls: ast.ClassDef) -> list[tuple[str, ast.expr | None]]:
    """Class-level fields and `self.X: T = ...` declared in __init__, as (name, annotation)."""
    fields: list[tuple[str, ast.expr | None]] = []
    for node in cls.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            fields.append((node.target.id, node.annotation))
        elif isinstance(node, ast.Assign):
            fields += [(t.id, None) for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.FunctionDef) and node.name == "__init__":
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Attribute):
                    fields.append((stmt.target.attr, stmt.annotation))
    return [(name, annotation) for name, annotation in fields if not name.startswith("_")]

def nested_classes(cls: ast.ClassDef) -> list[ast.ClassDef]:
    return [n for n in cls.body if isinstance(n, ast.ClassDef)]

def annotations(cls: ast.ClassDef) -> list[ast.expr]:
    """Every annotation in the public API of the class (including nested classes)."""
    result = [annotation for _, annotation in public_fields(cls) if annotation]
    for method in public_methods(cls):
        result += [a.annotation for a in method.args.args if a.annotation]
        if method.returns:
            result.append(method.returns)
    for nested in nested_classes(cls):
        result += annotations(nested)
    return result

def collect_used_classes(classes: dict[str, ast.ClassDef] | None = None) -> list[ast.ClassDef]:
    """ROOT + every class referenced from its annotations (transitively)."""
    classes = classes if classes is not None else collect_classes()
    used: dict[str, ast.ClassDef] = {}
    queue = [ROOT]
    while queue:
        name = queue.pop(0)
        if name in used or name not in classes:
            continue
        used[name] = classes[name]
        queue += [n.id for a in annotations(classes[name]) for n in ast.walk(a) if isinstance(n, ast.Name)]
    return list(used.values())

def main() -> None:
    from generate_python_stubs import write_stub as write_python_stub
    from generate_lua_stubs import write_stub as write_lua_stub

    write_python_stub()
    write_lua_stub()

if __name__ == "__main__":
    main()
