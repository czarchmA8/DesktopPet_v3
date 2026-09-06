"""Builds applications and creates exe file using PyInstaller."""

import time
import shutil
from pathlib import Path

import PyInstaller.__main__

import config

# Resources packed inside .exe (read-only)
RESOURCES_TO_INCLUDE = [
    "Assets/",
    "translations/*.qm",
    "icon.ico",
    "settings.default.json",
    "version.json",
]
# Resources next to the .exe file that the user has access to (for saving logs/database/settings)
USER_RESOURCES_TO_COPY = [
    "Mods/"
]

def copy_files(project_root: Path, app_dist_dir: Path) -> None:
    """Copy runtime resources from the project into the build output directory."""
    for item_name in USER_RESOURCES_TO_COPY:
        src = project_root / item_name
        dst = app_dist_dir / item_name

        if not src.exists():
            print(f'[!] Warning: "{src}" does not exist, skipping.')
            continue

        if src.is_dir():
            print(f'Copying folder "{src}" -> "{dst}"...')
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            print(f'Copying file "{src}" -> "{dst}"...')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    print("[✅] Application files and folders copied.")

def get_option(question: str, default_option: str | None=None):
    options = ["y", "n"]

    show_options = options.copy()
    if default_option:
        default_option = default_option.lower()
        show_options[show_options.index(default_option)] = default_option.upper()
    show_options_str = '/'.join(show_options)
    
    while True:
        option = input(f"{question} ({show_options_str}): ").lower()
        
        if option == "" and default_option:
            return default_option
        elif option in options:
            return option
        else:
            print("[ERROR] Unknown option.")

def main() -> None:
    """Builds the executable and optionally bundle resources."""
    print(f"App name: {config.APP_NAME}")
    print(f"Project root: {config.APP_DIR}")
    
    option_update_translations = get_option("Update translations?", "y")
    option_run_tests = get_option("Run tests?", "y")
    option_copy_mods = get_option("Build the app with copied mods?", None)
    start_time = time.perf_counter()

    if option_update_translations == "y":
        from tools import update_languages
        print('[#] Updating ".ts" files...')
        update_languages.update_ts_files(update_languages.TS_DIR, update_languages.LANG_CODES)

        print('[#] Updating ".qm" files...')
        update_languages.update_qm_files(update_languages.TS_DIR, update_languages.QM_DIR, update_languages.LANG_CODES)

    if option_run_tests == "y":
        from tools.run_tests import run_tests as run_tests_main
        run_tests_main()

    main_file_path = config.APP_DIR / "main.py"
    icon_file_path = config.APP_DIR / "icon.ico"

    dist_dir_path = config.APP_DIR / "tools" / "output" / "Build"
    spec_file_path = dist_dir_path / f"{config.APP_NAME}.spec"
    work_dir_path = dist_dir_path / "Temp"

    if not main_file_path.is_file():
        raise FileNotFoundError(f'File "{main_file_path}" does not exist.')
    if not icon_file_path.is_file():
        raise FileNotFoundError(f'File "{icon_file_path}" does not exist.')

    if dist_dir_path.is_dir():
        print(f'Removing directory "{dist_dir_path}"...')
        shutil.rmtree(dist_dir_path)
        print(f'Directory "{dist_dir_path}" has been removed.')

    print("Building executable...")

    add_data_args = []
    for item in RESOURCES_TO_INCLUDE:
        if any(ch in item for ch in "*?["):
            matches = list(config.APP_DIR.glob(item))
            if not matches:
                print(f'[!] Warning: no files match "{item}", skipping.')
                continue

            dst_rel = str(Path(item).parent)
            for src_path in matches:
                add_data_args.extend(["--add-data", f"{src_path};{dst_rel}"])
        else:
            src_path = config.APP_DIR / item

            if src_path.exists():
                dst_rel = item if src_path.is_dir() else "."
                add_data_args.extend(["--add-data", f"{src_path};{dst_rel}"])
            else:
                print(f'[!] Warning: "{src_path}" does not exist, skipping.')

    PyInstaller.__main__.run(
        [
            str(main_file_path),
            "--onedir",
            "--windowed",
            f"--icon={icon_file_path}",
            f"--name={config.APP_NAME}",
            "--clean",
            "--specpath", str(spec_file_path.parent),
            "--workpath", str(work_dir_path),
            "--distpath", str(dist_dir_path),
            "--collect-all", "lupa",
        ]
        + add_data_args
    )

    if spec_file_path.is_file():
        print(f'Removing file "{spec_file_path}"...')
        spec_file_path.unlink()
        print(f'File "{spec_file_path}" has been removed.')

    if work_dir_path.is_dir():
        print(f'Removing directory "{work_dir_path}"...')
        shutil.rmtree(work_dir_path)
        print(f'Directory "{work_dir_path}" has been removed.')

    app_dist_dir = dist_dir_path / config.APP_NAME
    if option_copy_mods == "y":
        copy_files(config.APP_DIR, app_dist_dir)

    print(f'[✅] Application built at "{app_dist_dir}"')
    end_time = time.perf_counter()
    execution_time = end_time - start_time
    print(f"Execution time: {round(execution_time)} seconds")

if __name__ == "__main__":
    main()
