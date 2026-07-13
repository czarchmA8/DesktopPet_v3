import pytest # noqa: F401
from pathlib import Path
from types import ModuleType
import shutil

PROJECT_ROOT = Path(__file__).parent.parent

def _load_update_languages_module() -> ModuleType:
    '''
    Dynamically loads the language updater utility module.

    Returns:
        ModuleType: The imported update_languages module.
    '''
    from tools import update_languages
    assert update_languages is not None, "Failed to load the update_languages module."
    return update_languages

update_languages = _load_update_languages_module()
TS_DIR: Path = update_languages.TS_DIR
QM_DIR: Path = update_languages.QM_DIR
TEMP_DIR: Path = PROJECT_ROOT / "tools" / "output" / "temp_tests"
SOURCE_FILES: list[Path] = update_languages.SOURCE_FILES
LANG_CODES_TS: list[str] = update_languages.LANG_CODES

def test_at_least_one_language_defined() -> None:
    """Verifies that the application has at least one language."""
    assert len(LANG_CODES_TS) >= 1

def test_equal_number_of_file_translations() -> None:
    """Ensures that every defined .ts source translation file has a corresponding compiled .qm file."""
    lang_codes_qm: list[str] = sorted(file.stem for file in QM_DIR.iterdir() if file.suffix == ".qm")
    assert LANG_CODES_TS == lang_codes_qm, (
        f"Mismatched translation files! Configured .ts languages: {LANG_CODES_TS}, "
        f"but found compiled .qm files: {lang_codes_qm}."
    )

def test_translations_up_to_date() -> None:
    """Validates that all translation files (.ts and .qm) are fully synchronized with the source code
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
    update_languages.update_qm_files(TEMP_DIR, TEMP_DIR, LANG_CODES_TS)
    for lang_code in LANG_CODES_TS:
        original_file_path = QM_DIR / f"{lang_code}.qm"
        temp_file_path = TEMP_DIR / f"{lang_code}.qm"
        assert original_file_path.read_bytes() == temp_file_path.read_bytes(), (
            f"The {lang_code}.qm file is not up to date! "
            f"Run the translation updater tool to recompile the translation files."
        )

def test_the_translation_works_correctly() -> None:
    """Tests the runtime translation mechanism to ensure text dynamically switches between languages as expected."""
    from dashboard.translator import Translator
    from PySide6 import QtCore, QtWidgets
    QtWidgets.QApplication()
    
    translator = Translator("en")
    text = [""]
    translator.tr(lambda text=text: text.__setitem__(0, QtCore.QCoreApplication.translate("ControlWindow", "Settings", None)))
    assert text[0] == "Settings", f"Expected English translation to be 'Settings', but got '{text[0]}'."
    translator.change_language("pl")
    assert text[0] == "Ustawienia", f"Expected Polish translation to be 'Ustawienia', but got '{text[0]}'."
