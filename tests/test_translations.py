import pytest # noqa: F401
from pathlib import Path
from types import ModuleType
import shutil

from config import APP_DIR

def _load_update_languages_module() -> ModuleType:
    """
    Dynamically loads the language updater utility module.

    Returns:
        ModuleType: The imported update_languages module.
    """
    from tools import update_languages
    assert update_languages is not None, "Failed to load the update_languages module."
    return update_languages

update_languages = _load_update_languages_module()
TS_DIR: Path = update_languages.TS_DIR
QM_DIR: Path = update_languages.QM_DIR
TEMP_DIR: Path = APP_DIR / "tools" / "output" / "temp_tests"
SOURCE_FILES: list[Path] = update_languages.SOURCE_FILES
LANG_CODES_TS: list[str] = update_languages.LANG_CODES

def test_at_least_one_language_defined() -> None:
    """Verifies that the application has at least one language."""
    assert len(LANG_CODES_TS) >= 1

def test_translations_up_to_date() -> None:
    """Validates that all translation files (.ts) are fully synchronized with the source code
    and contain no untranslated (unfinished) strings.
    """
    if TEMP_DIR.exists() and TEMP_DIR.is_dir():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(exist_ok=True)
    for lang_code in LANG_CODES_TS:
        original_file_path = TS_DIR / f"{lang_code}.ts"
        shutil.copy(original_file_path, TEMP_DIR)

    update_languages.update_ts_files(TEMP_DIR, LANG_CODES_TS)
    for lang_code in LANG_CODES_TS:
        ts_content = (TEMP_DIR / f"{lang_code}.ts").read_text(encoding="utf-8")
        assert '<translation type="unfinished">' not in ts_content, (
            f"The {lang_code}.ts file contains unfinished/missing translations! "
            f"Please translate all new strings using Qt Linguist."
        )

def test_the_translation_works_correctly() -> None:
    """Tests the runtime translation mechanism to ensure text dynamically switches between languages as expected."""
    from dashboard.translator import Translator
    from PySide6 import QtCore, QtWidgets
    QtWidgets.QApplication()
    
    translator = Translator("en")
    text = [""]
    translator.tr(lambda text=text: text.__setitem__(0, QtCore.QCoreApplication.translate("MainWindow", "Settings", None)))
    assert text[0] == "Settings", f"Expected English translation to be 'Settings', but got '{text[0]}'."
    translator.change_language("pl")
    assert text[0] == "Ustawienia", f"Expected Polish translation to be 'Ustawienia', but got '{text[0]}'."
