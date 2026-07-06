# Automates the translation process for the application.

def main():
    import os
    from pathlib import Path

    current_dir = Path(__file__)
    PROJECT_ROOT = current_dir.parent.parent
    QM_DIR = PROJECT_ROOT / "translations"
    TS_DIR = PROJECT_ROOT / "tools" / "translations_raw"

    lang_codes = sorted(file.stem for file in TS_DIR.iterdir() if file.suffix == ".ts")

    print("Updating \".ts\" files")
    for lang_code in lang_codes:
        ts_file = TS_DIR / f"{lang_code}.ts"
        dash_py = PROJECT_ROOT / 'dashboard' / 'dashboard.py'
        obj_py = PROJECT_ROOT / 'dashboard' / 'objects_editor.py'

        os.system(f'pyside6-lupdate "{dash_py}" "{obj_py}" -ts "{ts_file}"')

    print("Opening pyside6-linguist")
    ts_files_args = " ".join(f'"{TS_DIR / f"{lang_code}.ts"}"' for lang_code in lang_codes)
    os.system(f"pyside6-linguist {ts_files_args}")

    print("Updating \".qm\" files")
    for lang_code in lang_codes:
        ts_file = TS_DIR / f"{lang_code}.ts"
        qm_file = QM_DIR / f"{lang_code}.qm"
        os.system(f'pyside6-lrelease "{ts_file}" -qm "{qm_file}"')

if __name__ == "__main__":
    main()
