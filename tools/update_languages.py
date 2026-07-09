# Automates the translation process for the application.
import subprocess
from pathlib import Path

PROJECT_ROOT: Path = Path(__file__).parent.parent
QM_DIR: Path = PROJECT_ROOT / "translations"
TS_DIR: Path = PROJECT_ROOT / "tools" / "translations_raw"
SOURCE_FILES: list[Path] = [
    PROJECT_ROOT / "dashboard" / "dashboard.py",
    PROJECT_ROOT / "dashboard" / "objects_editor.py",
]
LANG_CODES: list[str] = sorted(file.stem for file in TS_DIR.iterdir() if file.suffix == ".ts")

def update_ts_files(ts_dir: Path, lang_codes: list[str]) -> None:
    for lang_code in lang_codes:
        ts_file = ts_dir / f"{lang_code}.ts"

        cmd = ["pyside6-lupdate", *map(str, SOURCE_FILES), "-ts", str(ts_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, (f"pyside6-lupdate failed:\n{result.stdout}\n{result.stderr}")
        if result.stdout:
            print(result.stdout)

def open_linguist(ts_dir: Path, lang_codes: list[str]) -> None:
    ts_files_args = [str(ts_dir / f"{lang_code}.ts") for lang_code in lang_codes]
    cmd = ["pyside6-linguist", *ts_files_args]
    subprocess.run(cmd, capture_output=False, text=False)

def update_qm_files(ts_dir: Path, qm_dir: Path, lang_codes: list[str]) -> None:
    for lang_code in lang_codes:
        ts_file = ts_dir / f"{lang_code}.ts"
        qm_file = qm_dir / f"{lang_code}.qm"
        cmd = ["pyside6-lrelease", str(ts_file), "-qm", str(qm_file)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, (f"pyside6-lrelease failed:\n{result.stdout}\n{result.stderr}")
        if result.stdout:
            print(result.stdout)

def main() -> None:
    print("[#] Updating \".ts\" files...")
    update_ts_files(TS_DIR, LANG_CODES)

    print("[#] Opening pyside6-linguist...")
    open_linguist(TS_DIR, LANG_CODES)

    print("[#] Updating \".qm\" files...")
    update_qm_files(TS_DIR, QM_DIR, LANG_CODES)

if __name__ == "__main__":
    main()
