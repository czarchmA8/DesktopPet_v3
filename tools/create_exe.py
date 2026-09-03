"""Builds applications and creates exe file using PyInstaller."""

import shutil
from pathlib import Path

import pathspec
import PyInstaller.__main__

import config

# Resources packed inside .exe (read-only)
RESOURCES_TO_INCLUDE = [
    "Assets",
    "translations",
    "icon.ico",
    "settings.default.json",
    "version.json",
]
# Resources next to the .exe file that the user has access to (for saving logs/database/settings)
USER_RESOURCES_TO_COPY = [
    "Mods"
]

def build_gitignore_spec(project_root: Path) -> pathspec.PathSpec:
    """Build a pathspec matcher from the project's `.gitignore` rules."""
    gitignore_patterns = (project_root / ".gitignore").read_text(encoding="utf-8").split("\n")

    exclude_path = project_root / ".git" / "info" / "exclude"
    exclude_patterns = exclude_path.read_text(encoding="utf-8").split("\n") if exclude_path.is_file() else []

    gitignore_patterns = gitignore_patterns + exclude_patterns + [".git/"]
    gitignore_patterns = [x for x in gitignore_patterns if x != "" and x[0] != "#"]

    return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, gitignore_patterns)

def copy_files(project_root: Path, app_dist_dir: Path, spec: pathspec.PathSpec) -> None:
    """Copy runtime resources from the project into the build output directory."""
    for item_name in USER_RESOURCES_TO_COPY:
        src = project_root / item_name
        dst = app_dist_dir / item_name

        if not src.exists():
            print(f'[!] Warning: "{src}" does not exist, skipping.')
            continue

        if src.is_dir():
            print(f'Copying folder "{src}" -> "{dst}"...')

            def ignore_gitignored(current_dir: str, names: list[str]) -> list[str]:
                """`shutil.copytree` ignore-callback that filters out gitignored entries."""
                current_path = Path(current_dir)
                ignored = []
                for name in names:
                    rel_path = (current_path / name).relative_to(project_root)
                    rel_str = rel_path.as_posix()
                    if (current_path / name).is_dir():
                        rel_str += "/"
                    if spec.match_file(rel_str):
                        ignored.append(name)
                return ignored

            shutil.copytree(src, dst, ignore=ignore_gitignored, dirs_exist_ok=True)
        else:
            print(f'Copying file "{src}" -> "{dst}"...')
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)

    print("[✅] Application files and folders copied.")

def main() -> None:
    """Builds the executable and optionally bundle resources."""
    print(f"App name: {config.APP_NAME}")
    print(f"Project root: {config.APP_DIR}")

    while True:
        option = input("Run tests? (y/n): ").lower()
        if option in ("y", "n"):
            break
        else:
            print("[ERROR] Unknown option.")

    if option == "y":
        from tools.run_tests import run_tests as run_tests_main
        run_tests_main()

    while True:
        option = input("Build the app with copied folders? (y/n): ").lower()
        if option in ("y", "n"):
            break
        else:
            print("[ERROR] Unknown option.")

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
        src_path = config.APP_DIR / item

        if src_path.exists():
            dst_rel = item if src_path.is_dir() else "."

            # Format: "source_absolute_path;destination_relative_path"
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
            "--specpath",
            str(spec_file_path.parent),
            "--workpath",
            str(work_dir_path),
            "--distpath",
            str(dist_dir_path),
        ] + add_data_args
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
    if option == "y":
        spec = build_gitignore_spec(config.APP_DIR)
        copy_files(config.APP_DIR, app_dist_dir, spec)

    print(f'[✅] Application built at "{app_dist_dir}"')

if __name__ == "__main__":
    main()
