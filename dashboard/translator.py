import sys
import inspect
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTranslator

class Translator:
    '''
    Manages dynamic language switching within the application, allowing on-the-fly text updates without requiring a restart.

    Translation Workflow (Qt/PySide):
    1. Extract/Update strings: Run `pyside6-lupdate dashboard/dashboard.py dashboard/objects_editor.py -ts translations/en.ts` to scan the code for translatable text.
    2. Translate: Open the `.ts` file in `pyside6-linguist` (or a text editor) and add your translations.
    3. Compile: Run `pyside6-lrelease translations/en.ts` to generate the compiled `.qm` file used by the application.

    In the `tools/` folder there is a script `update_languages.py` to automate translation updates.
    '''
    def __init__(self, lang_code: str):
        self._calls: dict[str, list] = {}
        self._translator = QTranslator()
        self.change_language(lang_code)

    def tr(self, func, owner: str | None=None):
        """
        Registers and executes a translation callback function.

        Example:
            translator.tr(lambda show_action=show_action: show_action.setText(
                QtCore.QCoreApplication.translate("tray-icon", "Show Panel", None)
            ))
        """
        ramka = inspect.stack()[1]
        modul = inspect.getmodule(ramka.frame)
        if modul is None:
            owner_name = owner if owner else "unknown"
        else:
            owner_name = owner if owner else modul.__name__
        self._calls.setdefault(owner_name, []).append(func)
        func()

    def retranslate_all(self) -> None:
        for owner in self._calls:
            for func in self._calls[owner]:
                try:
                    func()
                except RuntimeError:
                    self._calls[owner].remove(func)
                    continue

    def delete_calls_from_owner(self, owner: str) -> None:
        if owner in self._calls:
            del self._calls[owner]

    def change_language(self, lang_code: str) -> None:
        app = QApplication.instance()
        assert isinstance(app, QApplication), "QApplication must exist before creating HitboxOverlay"
        app.removeTranslator(self._translator)
        if getattr(sys, "frozen", False):
            base_dir = Path(sys.executable).parent
        else:
            base_dir = Path(__file__).parent.parent
        qm_path = base_dir / "translations" / f"{lang_code}.qm"
        if qm_path.is_file():
            ok = self._translator.load(str(qm_path))
            if not ok:
                raise RuntimeError(f'QTranslator failed to load "{qm_path}" (invalid or incompatible .qm file).')
        else:
            raise FileNotFoundError(f'File "{qm_path}" does not exist.')
        app.installTranslator(self._translator)
        self.retranslate_all()
