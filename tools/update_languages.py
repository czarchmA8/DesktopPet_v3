"""Translation workflow automation.

Automates the Qt-based translation cycle for the application:
    1. Regenerate `.ts` raw translation source files from the current source code.
        Note: Translatable strings must be static literals (avoid f-strings; use %1, %2 for variables).
    2. Open Qt Linguist (`pyside6-linguist`) so a translator can review and
        fill in/update the actual translated strings for each language.
    3. Compile the updated `.ts` files into binary `.qm` files,
        which is the format the application loads at runtime.
"""

import subprocess
from pathlib import Path
import pathspec

import config

QM_DIR: Path = config.APP_DIR / "translations"
TS_DIR: Path = config.APP_DIR / "translations"
SOURCE_FILES: list[str] = [
    "dashboard/"
]
available_codes: set[str] = {file.stem for file in TS_DIR.iterdir() if file.suffix == ".ts"}
print(f"LANG_CODES: {available_codes}")
user_order: list[str] = ["en", "pl", "es", "fr", "de", "hi"]
LANG_CODES: list[str] = [code for code in user_order if code in available_codes]

def resolve_source_files(project_root: Path, patterns: list[str]) -> list[Path]:
    spec = pathspec.PathSpec.from_lines("gitignore", patterns)

    matched_files = []
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix not in (".py",):
            continue
        rel_path = path.relative_to(project_root).as_posix()
        if spec.match_file(rel_path):
            matched_files.append(path)

    return matched_files

def update_ts_files(ts_dir: Path, lang_codes: list[str], no_obsolete: bool=False) -> None:
    """Regenerate `.ts` translation source files from the current source code."""
    source_files = resolve_source_files(config.APP_DIR, SOURCE_FILES)

    if not source_files:
        print("[!] Warning: no files matched SOURCE_FILES patterns.")

    for lang_code in lang_codes:
        ts_file = ts_dir / f"{lang_code}.ts"

        cmd = ["pyside6-lupdate", "-locations", "none", *map(str, source_files), "-ts", str(ts_file)]
        if no_obsolete:
            cmd.insert(1, "-no-obsolete")
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, (f"pyside6-lupdate failed:\n{result.stdout}\n{result.stderr}")
        if result.stdout:
            print(result.stdout)

def open_linguist(ts_dir: Path, lang_codes: list[str]) -> None:
    """Open Qt Linguist with all language `.ts` files for manual translation."""
    ts_files_args = [str(ts_dir / f"{lang_code}.ts") for lang_code in lang_codes]
    cmd = ["pyside6-linguist", *ts_files_args]
    subprocess.run(cmd, capture_output=False, text=False)

def update_qm_files(ts_dir: Path, qm_dir: Path, lang_codes: list[str]) -> None:
    """Compile `.ts` translation source files into binary `.qm` files."""
    for lang_code in lang_codes:
        ts_file = ts_dir / f"{lang_code}.ts"
        qm_file = qm_dir / f"{lang_code}.qm"
        cmd = ["pyside6-lrelease", str(ts_file), "-qm", str(qm_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, (f"pyside6-lrelease failed:\n{result.stdout}\n{result.stderr}")
        if result.stdout:
            print(result.stdout)

def get_option(question: str, default_option: str | None = None):
    options = ["y", "n"]

    show_options = options.copy()
    if default_option:
        default_option = default_option.lower()
        show_options[show_options.index(default_option)] = default_option.upper()
    show_options_str = "/".join(show_options)

    while True:
        option = input(f"{question} ({show_options_str}): ").lower()

        if option == "" and default_option:
            return default_option
        elif option in options:
            return option
        else:
            print("[ERROR] Unknown option.")

def main() -> None:
    """Runs the full translation update workflow."""
    option_no_obsolete = get_option("Delete obsolete translations?", "n")

    print("[#] Updating \".ts\" files...")
    option = True if option_no_obsolete == "y" else False
    update_ts_files(TS_DIR, LANG_CODES, no_obsolete=option)

    print("[#] Opening pyside6-linguist...")
    open_linguist(TS_DIR, LANG_CODES)

    print("[#] Updating \".qm\" files...")
    update_qm_files(TS_DIR, QM_DIR, LANG_CODES)

if __name__ == "__main__":
    main()
