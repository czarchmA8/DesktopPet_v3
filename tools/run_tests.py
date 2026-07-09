import os
from pathlib import Path
import sys
import importlib.metadata

import pytest # noqa: F401
import mypy # noqa: F401
import ruff # noqa: F401
import pipreqs # noqa: F401

def run_command(cmd: str, label: str) -> None:
    print(f"[#] Starting up \"{label}\": `{cmd}`")
    exit_code = os.system(cmd)
    if exit_code != 0:
        print(f"[X] Step \"{label}\" failed (code {exit_code}).")
        sys.exit(1)
    else:
        print(f"[X] Step \"{label}\" completed successfully.")

def main():
    MAIN_PATH = Path(__file__).parent.parent
    os.chdir(MAIN_PATH)

    print(f"pytest=={pytest.__version__}")
    print(f"pipreqs=={pipreqs.__version__}")
    print(f"mypy=={importlib.metadata.version('mypy')}")
    print(f"ruff=={importlib.metadata.version('ruff')}")
    
    print("[#] Getting the list of ignored folders...")
    ignore_list: list = []
    for ignore_path in (
        (MAIN_PATH / ".gitignore"),
        (MAIN_PATH / ".git" / "info" / "exclude"),
    ):
        for line in ignore_path.read_text(encoding="utf8").splitlines():
            line = line.strip()

            if not line or line.startswith("#") or line.startswith("!") or "*" in line:
                continue

            line = line.lstrip("/").rstrip("/")

            path = MAIN_PATH / line
            if path.is_dir():
                ignore_list.append(line)
    ignore_list = sorted(set(ignore_list))
    print(f"Ignored folders: {ignore_list}")

    run_command(
        "python -m ruff check . --select F",
        "Checking Code Formatting (Ruff)"
    )

    ignore_str: str = "(" + "|".join([f.replace(".", "\\.") for f in ignore_list]) + ")"
    run_command(
        f'python -m mypy . --ignore-missing-imports --exclude "{ignore_str}"',
        "Checking Code Formatting (MyPy)",
    )

    ignore_str = ",".join(ignore_list)
    requirements_path = MAIN_PATH / "tools" / "output" / "requirements.txt"
    run_command(
        f'pipreqs . --mode no-pin --savepath tools/output/requirements.txt --force --encoding=utf-8 --ignore "{ignore_str}"',
        "Checking library dependencies",
    )
    print(f"{str(requirements_path.relative_to(MAIN_PATH))}:")
    print(requirements_path.read_text("utf-8"))

    run_command(
        "python -m pytest tests/ -v --tb=short",
        "Running tests"
    )

    print("[#] All tests completed successfully")

if __name__ == "__main__":
    main()
