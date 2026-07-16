"""Local/CI code-quality pipeline runner.

Runs the quality-check pipeline used both locally and in CI:
    1. Ruff - static lint check.
    2. MyPy - static type checking across the project.
    3. Pipreqs - regenerates `tools/output/requirements.txt` from actual imports,
       used as a sanity check that `requirements.txt` stays in sync with the code.
    4. Pytest - runs the automated test suite in `tests/`.

Any step that fails (non-zero exit code) stops the pipeline immediately and
exits with status 1, so this script is suitable for use as a CI gate.
"""

import os
from pathlib import Path
import sys
import importlib.metadata

import pytest # noqa: F401
import mypy # noqa: F401
import ruff # noqa: F401
import pipreqs # noqa: F401

def run_command(cmd: str, label: str) -> None:
    """Run a shell command as a labeled pipeline step, aborting on failure."""
    print(f"[#] Starting up \"{label}\": `{cmd}`")
    exit_code = os.system(cmd)
    if exit_code != 0:
        print(f"[X] Step \"{label}\" failed (code {exit_code}).")
        sys.exit(1)
    else:
        print(f"[X] Step \"{label}\" completed successfully.")

def main():
    """Runs the quality-check pipeline."""
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
