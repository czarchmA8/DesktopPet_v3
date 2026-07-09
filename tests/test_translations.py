import pytest # noqa: F401
from pathlib import Path
from types import ModuleType
import shutil

PROJECT_ROOT = Path(__file__).parent.parent

def _load_update_languages_module() -> ModuleType:
    from tools import update_languages
    assert update_languages is not None
    return update_languages

update_languages = _load_update_languages_module()
TS_DIR: Path = update_languages.TS_DIR
QM_DIR: Path = update_languages.QM_DIR
TEMP_DIR: Path = PROJECT_ROOT / "tools" / "output" / "temp_tests"
SOURCE_FILES: list[Path] = update_languages.SOURCE_FILES
LANG_CODES_TS: list[str] = update_languages.LANG_CODES

def test_at_least_one_language_defined() -> None:
    assert len(LANG_CODES_TS) >= 1

def test_equal_number_of_file_translations() -> None:
    lang_codes_qm: list[str] = sorted(file.stem for file in QM_DIR.iterdir() if file.suffix == ".qm")
    assert LANG_CODES_TS == lang_codes_qm

def test_translations_up_to_date() -> None:
    if TEMP_DIR.exists() and TEMP_DIR.is_dir():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(exist_ok=True)
    for lang_code in LANG_CODES_TS:
        original_file_path = TS_DIR / f"{lang_code}.ts"
        shutil.copy(original_file_path, TEMP_DIR)
    
    # `.ts` files
    update_languages.update_ts_files(TEMP_DIR, LANG_CODES_TS)
    for lang_code in LANG_CODES_TS:
        original_file_path = TS_DIR / f"{lang_code}.ts"
        original_file_content = original_file_path.read_text(encoding="utf-8")

        temp_file_path = TEMP_DIR / f"{lang_code}.ts"
        temp_file_content = temp_file_path.read_text(encoding="utf-8").replace("<location filename=\"../../../", "<location filename=\"../../")

        assert original_file_content == temp_file_content

    # `.qm` files
    update_languages.update_qm_files(TS_DIR, TEMP_DIR, LANG_CODES_TS)
    for lang_code in LANG_CODES_TS:
        original_file_path = QM_DIR / f"{lang_code}.qm"
        temp_file_path = TEMP_DIR / f"{lang_code}.qm"
        assert original_file_path.read_bytes() == temp_file_path.read_bytes()

def test_the_translation_works_correctly() -> None:
    from dashboard.translator import Translator
    from PySide6 import QtCore, QtWidgets
    QtWidgets.QApplication()
    
    translator = Translator("en")
    text = [""]
    translator.tr(lambda text=text: text.__setitem__(0, QtCore.QCoreApplication.translate("ControlWindow", "Settings", None)))
    assert text[0] == "Settings"
    translator.change_language("pl")
    assert text[0] == "Ustawienia"
