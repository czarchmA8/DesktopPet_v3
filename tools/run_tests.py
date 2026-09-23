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
import subprocess
import sys
import importlib.metadata
import pathspec

import pytest # noqa: F401
import mypy # noqa: F401
import ruff # noqa: F401
import pipreqs # noqa: F401

import config

TOOLS = ("ruff", "mypy", "pipreqs", "pytest")

def run_command(cmd: list[str], label: str) -> None:
    """Run a shell command as a labeled pipeline step, aborting on failure."""
    print(f'[#] Starting up "{label}": `{" ".join(cmd)}`')
    process = subprocess.run(cmd)
    if process.returncode != 0:
        print(f'[X] Step "{label}" failed (code {process.returncode}).')
        sys.exit(1)
    print(f'[✅] Step "{label}" completed successfully.')

def get_ignored_dirs() -> list[str]:
    """Returns a list of ignored top-level folders based on `.gitignore` and `.git/info/exclude`."""
    gitignore_lines: list[str] = []

    for gitignore_file in (config.APP_DIR / ".gitignore", config.APP_DIR / ".git" / "info" / "exclude"):
        if gitignore_file.is_file():
            gitignore_lines.extend(gitignore_file.read_text(encoding="utf-8").splitlines())
    spec = pathspec.GitIgnoreSpec.from_lines(gitignore_lines)

    ignored_dirs: set[str] = set()
    for entry in config.APP_DIR.iterdir():
        if entry.is_dir():
            rel_path = entry.relative_to(config.APP_DIR).as_posix()
            if spec.match_file(f"{rel_path}/"):
                ignored_dirs.add(rel_path)

    return sorted(ignored_dirs)

def run_ruff() -> None:
    run_command(["uv", "run", "ruff", "check", ".", "--select", "F"], "Lint (Ruff)")

def run_mypy() -> None:
    run_command(
        ["uv", "run", "mypy", ".", "--ignore-missing-imports", "--exclude-gitignore"],
        "Type check (MyPy)",
    )

def run_pipreqs(ignored_dirs: list[str]) -> None:
    requirements_path = config.APP_DIR / "tools" / "output" / "requirements.txt"
    requirements_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["uv", "run", "pipreqs", ".", "--mode", "no-pin", "--savepath", str(requirements_path), "--force", "--encoding=utf-8"]

    if ignored_dirs:
        cmd += ["--ignore", ",".join(ignored_dirs)]
    run_command(cmd, "Library dependencies (Pipreqs)")

    print(f"{requirements_path.relative_to(config.APP_DIR)}:")
    print(requirements_path.read_text("utf-8"))

def run_pytest() -> None:
    run_command(["uv", "run", "pytest", "tests/", "-v", "--tb=short"], "Tests (Pytest)")

def run_tests() -> None:
    """Runs the quality-check pipeline."""
    os.chdir(config.APP_DIR)
    for tool in TOOLS:
        print(f"{tool}=={importlib.metadata.version(tool)}")

    ignored_dirs = get_ignored_dirs()
    print(f"Ignored folders: {ignored_dirs}")

    run_ruff()
    run_mypy()
    run_pipreqs(ignored_dirs)
    run_pytest()

    print("[#] All tests completed successfully")

if __name__ == "__main__":
    run_tests()
