import sys
from dataclasses import dataclass, field
from pathlib import Path
import json
import winreg
import logging
from typing import Callable
import requests
import time
from datetime import datetime

import keyboard
from PySide6.QtCore import (
    Qt, QCoreApplication, Signal,
    QLocale, QSize, QEvent
)
from PySide6.QtWidgets import (
    QApplication, QListWidgetItem, QMenu,
    QMessageBox, QMainWindow, QSystemTrayIcon,
    QDialog, QLabel, QPushButton
)
from PySide6.QtGui import QIcon, QPixmap, QImageReader

import config
from logger_setup import setup_process_logger
from dashboard.objects_editor import MainWindow as ObjectsEditorWindow
from dashboard.translator import Translator, replace_format
from dashboard.ui.ui_main_window import Ui_MainWindow
from dashboard.widgets.shortcut_edit import HotkeyDialog
from dashboard.widgets.mod_row import Ui_Form_mod_row
from dashboard.widgets.update_dialog import UpdateDialog
from dashboard.widgets.category_sep import CategorySeparator

MODS_DIR = config.APP_DIR / "Mods"

logger: logging.Logger = logging.getLogger(__name__)

@dataclass
class Mod:
    """A single mod entry."""
    id: str
    name: str
    author: str = "unknown"
    version: str = "0.0.0"
    description: str = "No description available."
    dependencies: dict[str, str] = field(default_factory=dict)
    preview_path: Path | None = None
    active: bool = True

@dataclass
class Entity:
    id: str
    name: str
    mod_id: str
    preview_path: Path
    description: str = ""

@dataclass
class HotkeyBinding:
    """Stores widgets for keyboard shortcuts"""
    label_shortcut: QLabel
    button_set: QPushButton
    button_remove: QPushButton
    callback: Callable

class MainWindow(QMainWindow):
    """Main control panel window for application"""

    exit_requested = Signal()
    translate = QCoreApplication.translate

    def __init__(self, conn, shared_data, translator):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)

        self.setWindowIcon(QIcon(str(config.RESOURCE_DIR / "icon.ico")))

        self.conn = conn
        self.shared_data = shared_data
        self.translator = translator

        self.hwnd_self = int(self.winId())
        self.editor_window: ObjectsEditorWindow | None = None
        self.mods: dict[str, Mod] = {}
        self.entities: dict[str, Entity] = {}
        self._category_header_items: list[tuple[QListWidgetItem, CategorySeparator]] = []

        self._setup_hotkeys()

        self.setup_connections()

        self.load_mods()
        self.load_entities()

        self.retranslate_ui()

        self.exit_requested.connect(QCoreApplication.quit)

    def setup_connections(self) -> None:
        # === Settings ===
        
        # > Language
        LANG_DIR = config.RESOURCE_DIR / "translations"
        lang_codes = sorted(file.stem for file in LANG_DIR.iterdir() if file.suffix == ".qm")
        for lang_code in lang_codes:
            name = QLocale(lang_code).nativeLanguageName().capitalize() or lang_code
            self.ui.comboBox_language.addItem(name, lang_code)
        current_lang = self.shared_data.settings["language"]
        idx = self.ui.comboBox_language.findData(current_lang)
        self.ui.comboBox_language.setCurrentIndex(idx if idx >= 0 else 0)
        self.ui.comboBox_language.currentIndexChanged.connect(self._on_combobox_language_change)
        
        # > Sound
        self.ui.horizontalSlider_volume.setValue(self.shared_data.settings["volume"])
        self.ui.horizontalSlider_volume.valueChanged.connect(self._on_slider_volume_changes)
        self.ui.horizontalSlider_volume.sliderReleased.connect(self._on_slider_volume_release)
        self._on_slider_volume_changes(self.shared_data.settings["volume"])
        
        # > Entities
        self.ui.pushButton_open_objects_editor.clicked.connect(self.open_object_editor)

        for category in self.hotkeys_widgets:
            for key in self.hotkeys_widgets[category]:
                self.hotkeys_widgets[category][key].button_set.clicked.connect(lambda e, category=category, key=key: self._set_hotkey(category, key))
                self.hotkeys_widgets[category][key].button_remove.clicked.connect(lambda e, category=category, key=key: self._remove_hotkey(category, key))
                seq = self.shared_data.settings["hotkeys"][category][key]
                self.hotkeys_widgets[category][key].button_remove.setEnabled(seq is not None)
                if seq:
                    self.hotkeys_widgets[category][key].label_shortcut.setText(seq)
                else:
                    self.translator.tr(lambda category=category, key=key: self.hotkeys_widgets[category][key].label_shortcut.setText(self.translate("MainWindow", "No keyboard shortcut", None)))
        
        # > System
        self.ui.checkBox_check_for_updates.setChecked(self.shared_data.settings["check_for_updates"])
        self.ui.checkBox_check_for_updates.toggled.connect(self._on_check_for_updates_toggle)

        self.ui.checkBox_autostart.setChecked(self.shared_data.settings["autostart"])
        is_executable = getattr(sys, 'frozen', False)
        self.ui.checkBox_autostart.setEnabled(is_executable)
        if not is_executable:
            self.ui.checkBox_autostart.setToolTip(self.translate("MainWindow", "Autostart is only available for the packaged application, not for the script being run.", None))
        self.ui.checkBox_autostart.toggled.connect(self._on_autostart_toggle)
        
        # > Advanced
        self.ui.checkBox_debug_mode.setChecked(self.shared_data.settings["debug"]["active"])
        self.ui.checkBox_debug_mode.toggled.connect(self.update_debug_visibility)

        self.ui.checkBox_hitboxes_overlay.setChecked(self.shared_data.settings["debug"]["hitbox_overlay"])
        self.ui.checkBox_hitboxes_overlay.toggled.connect(self.update_debug_visibility)

        self.ui.checkBox_debug_information_window.setChecked(self.shared_data.settings["debug"]["debug_window"])
        self.ui.checkBox_debug_information_window.toggled.connect(self.update_debug_visibility)

        self.update_debug_check_states()
        
        # === Mods ===
        self.ui.listWidget_mods.currentRowChanged.connect(self._on_mod_selected)
        self.ui.pushButton_mod_settings.clicked.connect(self._on_mod_settings)
        self.ui.pushButton_load_mod_list.clicked.connect(self._on_load_mod_list)
        self.ui.pushButton_save_mod_list.clicked.connect(self._on_save_mod_list)
        self.ui.pushButton_discard_mod_changes.clicked.connect(self._on_discard_changes)
        self.ui.pushButton_save_mod_changes.clicked.connect(self._on_save_changes)
        
        # === Entities ===
        self.ui.listWidget_add_entities_list.currentItemChanged.connect(self._on_add_entity_selected)

        # === Info ===
        self.ui.pushButton_check_for_updates.clicked.connect(self._on_check_for_updates)
        self.last_time_checked: float | None = None
        self.update_check_cooldown: int = 0
        self.latest_release_info: dict | int | None = None
        if self.shared_data.settings["check_for_updates"]:
            self._on_check_for_updates()
        self.ui.pushButton_update_application.clicked.connect(self.on_click_update)

    def _setup_hotkeys(self) -> None:
        def _add_hotkey(sequence, callback):
            """Registers hotkey if sequence is not None/empty, otherwise returns None."""
            if sequence:
                try:
                    return keyboard.add_hotkey(sequence, callback)
                except Exception as e:
                    logger.error(f"[Hotkey] Failed to register '{sequence}': {e}")
            return None
        
        self.hotkeys_widgets = {
            "app": {
                "show": HotkeyBinding(
                    label_shortcut = self.ui.label_show_shortcut_value,
                    button_set = self.ui.pushButton_show_shortcut_set,
                    button_remove = self.ui.pushButton_show_shortcut_remove,
                    callback = self._show_and_focus_window,
                ),
                "hide": HotkeyBinding(
                    label_shortcut = self.ui.label_hide_shortcut_value,
                    button_set = self.ui.pushButton_hide_shortcut_set,
                    button_remove = self.ui.pushButton_hide_shortcut_remove,
                    callback = lambda: self.hide(),
                ),
                "exit": HotkeyBinding(
                    label_shortcut = self.ui.label_close_shortcut_value,
                    button_set = self.ui.pushButton_close_shortcut_set,
                    button_remove = self.ui.pushButton_close_shortcut_remove,
                    callback = lambda: self.exit_requested.emit(),
                ),
            },
            "entities": {
                "kill all": HotkeyBinding(
                    label_shortcut = self.ui.label_kill_all_entities_shortcut_value,
                    button_set = self.ui.pushButton_kill_all_entities_shortcut_set,
                    button_remove = self.ui.pushButton_kill_all_entities_shortcut_remove,
                    callback = lambda: (self.clear_all_objects(), print("TODO: kill all entities")),
                ),
                "show all": HotkeyBinding(
                    label_shortcut = self.ui.label_show_all_entities_shortcut_value,
                    button_set = self.ui.pushButton_show_all_entities_shortcut_set,
                    button_remove = self.ui.pushButton_show_all_entities_shortcut_remove,
                    callback = lambda: print("TODO: show all entities"),
                ),
                "hide all": HotkeyBinding(
                    label_shortcut = self.ui.label_hide_all_entities_shortcut_value,
                    button_set = self.ui.pushButton_hide_all_entities_shortcut_set,
                    button_remove = self.ui.pushButton_hide_all_entities_shortcut_remove,
                    callback = lambda: print("TODO: hide all entities"),
                ),
                "kill": HotkeyBinding(
                    label_shortcut = self.ui.label_kill_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_kill_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_kill_selected_entity_shortcut_remove,
                    callback = lambda: print("TODO: kill entity"),
                ),
                "show": HotkeyBinding(
                    label_shortcut = self.ui.label_show_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_show_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_show_selected_entity_shortcut_remove,
                    callback = lambda: (self.conn.send(["show_pet"]), print("TODO: show entity")),
                ),
                "hide": HotkeyBinding(
                    label_shortcut = self.ui.label_hide_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_hide_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_hide_selected_entity_shortcut_remove,
                    callback = lambda: (self.conn.send(["hide_pet"]), print("TODO: hide entity")),
                ),
                "teleport": HotkeyBinding(
                    label_shortcut = self.ui.label_teleport_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_teleport_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_teleport_selected_entity_shortcut_remove,
                    callback = lambda: (self.conn.send(["teleport_pet"]), print("TODO: teleport entity")),
                ),
            },
        }
        hotkeys_settings: dict = self.shared_data.settings["hotkeys"]
        self.hotkeys: dict[str, dict] = {}
        for category in self.hotkeys_widgets:
            for key in self.hotkeys_widgets[category]:
                self.hotkeys.setdefault(category, {})[key] = _add_hotkey(hotkeys_settings[category][key], self.hotkeys_widgets[category][key].callback)
        # self.hotkeys["objects"]["create"] = {
        #     name: _add_hotkey(hotkeys_settings["objects"]["create"][name], lambda name=name: conn.send(["spawn_object", name]))
        #     for name in hotkeys_settings["objects"].get("create", {})
        #     if Path("Assets", "Objects", name).exists()
        # }

    def retranslate_ui(self):
        self.ui.retranslate_static_ui(self)
        # Settings

        # Mods
        self._update_mods_group_title()

        # List of entities

        # Add entity
        self._update_entities_add_group_title()

        # Info
        self.ui.label_app_version.setText(replace_format(self.translate("MainWindow", "version: %1  \u2022  %2", None), config.APP_VERSION, config.APP_VERSION_DATE))

        # Version
        self.ui.label_version.setText(replace_format(self.translate("MainWindow", "Version: %1", None), config.APP_VERSION))

    def _show_and_focus_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()
    
    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def closeEvent(self, event):
        """Hides window instead of closing"""
        event.ignore()
        self.hide()

    # ================= Mods =================

    def load_mods(self) -> None:
        """Skanuje MODS_DIR i wczytuje moda z każdego podfolderu zawierającego about.json."""
        self.ui.listWidget_mods.clear()
        self.mods.clear()

        for folder in sorted(MODS_DIR.iterdir()):
            if not folder.is_dir():
                continue
            mod = self._load_mod_from_folder(folder)
            logger.debug(f"Mod loaded: {mod}")
            if mod is not None:
                self._add_mod_row(mod)

        if self.ui.listWidget_mods.count():
            self.ui.listWidget_mods.setCurrentRow(0)
        self._update_mods_group_title()

    def _load_mod_from_folder(self, folder: Path) -> Mod | None:
        """Buduje Mod z folder/about.json. ID moda = nazwa folderu."""
        about_path = folder / "about.json"
        data = json.loads(about_path.read_text(encoding="utf-8"))

        supported_image_formats = {bytes(fmt.data()).decode("utf-8").lower() for fmt in QImageReader.supportedImageFormats()}
        for extension in supported_image_formats:
            preview_file = (folder / "preview").with_suffix(f".{extension}")
            if preview_file.exists():
                break
        else:
            preview_file = None

        return Mod(
            id=folder.name,
            name=data.get("name", folder.name),
            author=data.get("author", "unknown"),
            version=data.get("version", "0.0.0"),
            description=data.get("description", "No description available."),
            dependencies=data.get("dependencies", {}),
            preview_path=preview_file,
            active=bool(data.get("active", True))
        )

    def _add_mod_row(self, mod: Mod) -> None:
        self.mods[mod.id] = mod

        row_widget = Ui_Form_mod_row()

        row_widget.checkBox.setChecked(mod.active)
        row_widget.label.setText(mod.name)
        row_widget.checkBox.toggled.connect(lambda checked, m=mod: self._on_mod_toggled(m, checked))
        row_widget.toolButton.clicked.connect(lambda _=False, m=mod: self._on_mod_menu(m))

        item = QListWidgetItem()
        item.setSizeHint(row_widget.sizeHint())
        item.setData(Qt.ItemDataRole.UserRole, mod.id)
        self.ui.listWidget_mods.addItem(item)
        self.ui.listWidget_mods.setItemWidget(item, row_widget)

    def _update_mods_group_title(self) -> None:
        self.ui.groupBox_mods_list.setTitle(replace_format(self.translate("MainWindow", "Mods (%1)", None), len(self.mods)))

    def _mod_for_row(self, row: int) -> Mod | None:
        item = self.ui.listWidget_mods.item(row)
        if item is None:
            return None
        return self.mods[item.data(Qt.ItemDataRole.UserRole)]

    def _on_mod_selected(self, row: int) -> None:
        mod = self._mod_for_row(row)
        if mod is None:
            return
        if mod.preview_path:
            pixmap = QPixmap(str(mod.preview_path))
            self.ui.label_mod_preview.setPixmap(pixmap)
        else:
            self.ui.label_mod_preview.setPixmap(QPixmap())
        self.ui.label_mod_name.setText(mod.name)
        self.ui.label_mod_author.setText(mod.author)
        self.ui.label_mod_version.setText(mod.version)
        self.ui.label_mod_id.setText(mod.id)
        self.ui.label_mod_description.setText(mod.description)

    def _on_mod_toggled(self, mod: Mod, checked: bool) -> None:
        mod.active = checked
        logger.debug(f"[mods] {mod.name} -> {'active' if checked else 'inactive'}")

    def _on_mod_menu(self, mod: Mod) -> None:
        menu = QMenu(self)
        menu.addAction(self.translate("MainWindow", "Open folder", None), lambda: print(f"[mods] open folder: {mod.name}"))
        menu.addAction(self.translate("MainWindow", "Remove", None), lambda: print(f"[mods] remove: {mod.name}"))
        menu.exec(self.cursor().pos())

    def _on_mod_settings(self) -> None:
        mod = self._mod_for_row(self.ui.listWidget_mods.currentRow())
        if mod is None:
            QMessageBox.information(self, self.translate("MainWindow", "Mod settings", None), self.translate("MainWindow", "Select a mod first.", None))
            return
        QMessageBox.information(self, self.translate("MainWindow", "Mod settings", None), self.translate("MainWindow", "TODO: settings for %1", None).replace("%1", mod.name))

    def _on_load_mod_list(self) -> None:
        print("[mods] TODO: load mod list from disk")

    def _on_save_mod_list(self) -> None:
        print("[mods] TODO: save mod list to disk")

    def _on_discard_changes(self) -> None:
        print("[mods] TODO: discard changes")

    def _on_save_changes(self) -> None:
        print("[mods] TODO: save changes")

    # ================= Settings =================
    def save_settings_state(self) -> None:
        """
        Saves current settings to settings.json
        Usage example:
        ```
            settings = self.shared_data.settings
            settings["key"] = value
            self.shared_data.settings = settings
            self.save_settings_state()
        ```
        """

        try:
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.shared_data.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, self.translate("MainWindow", "File saving error", None), self.translate("MainWindow", "Failed to save settings: %x", None).replace("%x", str(e)))

    def _on_combobox_language_change(self, index):
        lang_code = self.ui.comboBox_language.itemData(index)
        settings = self.shared_data.settings
        settings["language"] = self.ui.comboBox_language.currentData()
        self.shared_data.settings = settings
        logger.debug((lang_code, self.shared_data.settings["language"]))
        self.save_settings_state()
        self.translator.change_language(lang_code)

    def _on_slider_volume_changes(self, value):
        self.ui.label_volume_percent.setText(f"{value}%")

    def _on_slider_volume_release(self):
        settings = self.shared_data.settings
        settings["volume"] = self.ui.horizontalSlider_volume.value()
        self.shared_data.settings = settings
        self.save_settings_state()

    def _set_hotkey(self, category: str, key: str):
        dialog = HotkeyDialog(self)
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        if dialog.exec():
            seq = dialog.final_sequence
            if not seq:
                return
            old = self.shared_data.settings["hotkeys"][category].get(key)
            if old:
                keyboard.remove_hotkey(old)

            settings = self.shared_data.settings
            settings["hotkeys"][category][key] = seq
            self.shared_data.settings = settings
            self.hotkeys[category][key] = keyboard.add_hotkey(seq, self.hotkeys_widgets[category][key].callback)
            self.hotkeys_widgets[category][key].label_shortcut.setText(seq)
            self.hotkeys_widgets[category][key].button_remove.setEnabled(True)
            self.save_settings_state()
            QMessageBox.information(self, self.translate("MainWindow", "Success", None), self.translate("MainWindow", "Assigned '%x'.", None).replace("%x", seq))

    def _remove_hotkey(self, category: str, key):
        seq = self.shared_data.settings["hotkeys"][category].get(key)
        if seq:
            keyboard.remove_hotkey(seq)
            self.hotkeys[category][key] = None

            settings = self.shared_data.settings
            settings["hotkeys"][category][key] = None
            self.shared_data.settings = settings
            self.save_settings_state()

            self.translator.tr(lambda: self.hotkeys_widgets[category][key].label_shortcut.setText(self.translate("MainWindow", "No keyboard shortcut", None)))
            self.hotkeys_widgets[category][key].button_remove.setEnabled(False)

            QMessageBox.information(self, self.translate("MainWindow", "Success", None), self.translate("MainWindow", "Shortcut removed.", None))
        else:
            QMessageBox.information(self, self.translate("MainWindow", "Information", None), self.translate("MainWindow", "No shortcut assigned.", None))

    def _on_check_for_updates_toggle(self, checked) -> None:
        settings = self.shared_data.settings
        settings["check_for_updates"] = self.ui.checkBox_check_for_updates.isChecked()
        self.shared_data.settings = settings
        self.save_settings_state()

    def _on_autostart_toggle(self, checked) -> None:
        """Toggles application autostart in Windows registry"""
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        if getattr(sys, 'frozen', False): # Jeśli program jest spakowany do .exe
            cmd = f'"{sys.executable}"'
        else: # Jeśli to surowy skrypt .py
            self.ui.checkBox_autostart.blockSignals(True)
            self.ui.checkBox_autostart.setChecked(False)
            self.ui.checkBox_autostart.blockSignals(False)
            QMessageBox.information(self, self.translate("MainWindow", "Autostart unavailable", None), self.translate("MainWindow", "Autostart is only available for the packaged application, not for the script being run.", None))
            return

            # Dodawanie skryptu do autostartu (porzucone)
            # pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
            # script_path = os.path.abspath(sys.argv[0])
            # # Dodajemy /d, aby Windows odpalił skrypt w jego folderze macierzystym
            # cmd = f'cmd.exe /c "cd /d "{os.path.dirname(script_path)}" && "{pythonw_path}" "{script_path}""'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
            if checked:
                winreg.SetValueEx(key, config.APP_NAME, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, config.APP_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            self.ui.checkBox_autostart.blockSignals(True)
            self.ui.checkBox_autostart.setChecked(not checked)
            self.ui.checkBox_autostart.blockSignals(False)
            QMessageBox.warning(self, self.translate("MainWindow", "Registry error", None), self.translate("MainWindow", "Failed to change autostart setting:\n%x", None).replace("%x", str(e)))

        settings = self.shared_data.settings
        settings["autostart"] = self.ui.checkBox_autostart.isChecked()
        self.shared_data.settings = settings
        self.save_settings_state()

    def update_debug_check_states(self):
        """Updates enabled/disabled state of debug checkboxes"""
        checked = self.ui.checkBox_debug_mode.isChecked()
        self.ui.checkBox_hitboxes_overlay.setEnabled(checked)
        self.ui.checkBox_debug_information_window.setEnabled(checked)

    def update_debug_visibility(self, checked: bool | None=None):
        """Updates visibility of debug overlays"""
        self.update_debug_check_states()

        settings = self.shared_data.settings
        settings["debug"]["active"] = self.ui.checkBox_debug_mode.isChecked()
        settings["debug"]["hitbox_overlay"] = self.ui.checkBox_hitboxes_overlay.isChecked()
        settings["debug"]["debug_window"] = self.ui.checkBox_debug_information_window.isChecked()
        self.shared_data.settings = settings
        self.save_settings_state()

        self.conn.send(["toggle_debug"])

    # ================= OBJECTS =================

    def clear_all_objects(self):
        """Removes all spawned objects from the world"""
        self.conn.send(["clear_all_objects"])

    def open_object_editor(self, image_path=None) -> None:
        if self.editor_window is not None:
            self.editor_window.destroy()
            self.editor_window = None
            self.translator.delete_calls_from_owner("dashboard.object_editor")
        if self.editor_window is None:
            self.editor_window = ObjectsEditorWindow(self.translator, image_path=image_path)
            assert isinstance(self.editor_window, ObjectsEditorWindow)
            self.editor_window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            self.editor_window.destroyed.connect(self._on_editor_window_closed)
            self.editor_window.show()
            self.editor_window.raise_()
            self.editor_window.activateWindow()

    def _on_editor_window_closed(self):
        self.editor_window = None
        self.translator.delete_calls_from_owner("dashboard.object_editor")

    # ================= ADD ENTITY =================

    def load_entities(self):
        sample_entities: list[Entity] = [
            Entity(
                id="ball",
                name="Ball",
                mod_id="more-balls",
                preview_path=MODS_DIR / "more-balls" / "entities"/ "ball" / "preview.png",
                description="A physically simulated ball bouncing off system windows"
            ),
            Entity(
                id="charmander",
                name="Charmander",
                mod_id="more-pets",
                preview_path=MODS_DIR / "more-pets" / "entities"/ "charmander" / "preview.jpg",
                description="Cute orange lizard"
            )
        ]

        self._populate_add_entities_list(sample_entities)

    def _make_square_pixmap(self, path: Path, size: int) -> QPixmap:
        """Loads preview.png and crops it to a size x size square (center-crop)."""
        src = QPixmap(str(path))
        if src.isNull():
            placeholder = QPixmap(size, size)
            placeholder.fill(Qt.GlobalColor.darkGray)
            return placeholder

        scaled = src.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = (scaled.width() - size) // 2
        y = (scaled.height() - size) // 2
        return scaled.copy(x, y, size, size)

    def _populate_add_entities_list(self, entities: list[Entity]) -> None:
        list_widget = self.ui.listWidget_add_entities_list
        list_widget.clear()
        list_widget.setUniformItemSizes(False)
        list_widget.setGridSize(QSize())

        icon_size: int = list_widget.iconSize().width()

        self.entities = {entity.id: entity for entity in entities}
        self._category_header_items.clear()

        entities_by_category: dict[str, list[Entity]] = {}
        for entity in entities:
            entities_by_category.setdefault(self.mods[entity.mod_id].name, []).append(entity)

        for category, category_entities in entities_by_category.items():
            # category separator
            header_item = QListWidgetItem()
            header_item.setFlags(Qt.ItemFlag.NoItemFlags)
            header_widget = CategorySeparator(category)
            list_widget.addItem(header_item)
            list_widget.setItemWidget(header_item, header_widget)
            self._category_header_items.append((header_item, header_widget))

            # entity tiles in this category
            for entity in category_entities:
                pixmap = self._make_square_pixmap(entity.preview_path, icon_size)
                item = QListWidgetItem(QIcon(pixmap), entity.name)
                item.setData(Qt.ItemDataRole.UserRole, entity.id)
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
                item.setSizeHint(QSize(88, 96))
                list_widget.addItem(item)

        self._update_category_header_widths()

        for row in range(list_widget.count()):
            item = list_widget.item(row)
            if item.data(Qt.ItemDataRole.UserRole) is not None:
                list_widget.setCurrentItem(item)
                break

        self._update_entities_add_group_title()
    
    def _update_entities_add_group_title(self):
        self.ui.groupBox_add_entities.setTitle(replace_format(self.translate("MainWindow", "Entities (%1)", None), len(self.entities)))

    def _update_category_header_widths(self) -> None:
        """Stretches category separators in the "Add" entity list to the current viewport width"""
        list_width = self.ui.listWidget_add_entities_list.viewport().width()
        for header_item, header_widget in self._category_header_items:
            header_item.setSizeHint(QSize(list_width, header_widget.sizeHint().height()))

    def _on_add_entity_selected(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        entity_id = current.data(Qt.ItemDataRole.UserRole)
        if entity_id is None:
            return  # ignore focus on category separator, not an actual entity

        entity = self.entities[entity_id]
        mod = self.mods[entity.mod_id]

        pixmap = QPixmap(str(entity.preview_path))
        self.ui.label_add_entity_preview.setPixmap(pixmap)
        self.ui.label_add_entity_name.setText(entity.name)
        self.ui.label_add_entity_mod_name.setText(mod.name)
        self.ui.label_add_entity_mod_id.setText(entity.mod_id)
        self.ui.label_add_entity_id.setText(entity.id)
        self.ui.label_add_entity_description.setText(entity.description)
    
    # ================= INFO =================

    def get_latest_release(self) -> dict | int:
        """Returns information about the latest release as a dictionary or status_code if an error is encountered"""
        url = f"https://api.github.com/repos/{config.APP_AUTHOR}/{config.REPO_NAME}/releases/latest"
        headers = {"User-Agent": "Python-Script"}

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()

            new_version = data["tag_name"]
            if new_version.startswith("v"):
                new_version = new_version[1:]

            published_at_formatted = datetime.fromisoformat(data["published_at"]).strftime("%Y-%m-%d, %H:%M")
            
            return {
                "tag": data["tag_name"],
                "version": new_version,
                "name": data["name"],
                "published_at": published_at_formatted,
                "url": data["html_url"],
            }
        else:
            return response.status_code

    def update_label_check_for_updates(self) -> None:
        if isinstance(self.latest_release_info, dict):
            if config.APP_VERSION != self.latest_release_info["version"]:
                self.ui.label_check_for_updates.setText(replace_format(self.translate("MainWindow", "New update \"%1\" from %2 available!", None), self.latest_release_info["version"], self.latest_release_info["published_at"]))
                self.ui.pushButton_update_application.setEnabled(True)
            else:
                self.ui.label_check_for_updates.setText(self.translate("MainWindow", "The application version is up to date", None))
        elif isinstance(self.latest_release_info, int):
            if self.latest_release_info == 404:
                self.ui.label_check_for_updates.setText(self.translate("MainWindow", "Repository not found or no versions published.", None))
            else:
                self.ui.label_check_for_updates.setText(replace_format(self.translate("MainWindow", "Error: %1", None), self.latest_release_info))
        elif self.latest_release_info is None:
            self.ui.label_check_for_updates.setText(self.translate("MainWindow", "The version has not been checked yet", None))
        else:
            raise Exception("This shouldn't have happened!")
    
    def _on_check_for_updates(self) -> None:
        now = time.time()
        if self.last_time_checked is None or now > self.last_time_checked + self.update_check_cooldown:
            self.last_time_checked = time.time()
            
            logger.debug("Checking for updates...")
            self.ui.label_check_for_updates.setText(self.translate("MainWindow", "Checking for updates...", None))
            
            self.latest_release_info = self.get_latest_release()
            
            if isinstance(self.latest_release_info, int):
                self.update_check_cooldown = 30
            else:
                self.update_check_cooldown = 60
            
            self.update_label_check_for_updates()
            logger.debug(self.ui.label_check_for_updates.text())
        else:
            time_elapsed = int((self.last_time_checked + self.update_check_cooldown) - now)
            logger.debug(f"You can check for updates again in {time_elapsed} seconds")

    def on_click_update(self):
        new_version = self.latest_release_info["version"]
        new_version_date = self.latest_release_info["published_at"]
        dialog = UpdateDialog(new_version, new_version_date, parent=self)
        result = dialog.exec()
        if result == QDialog.Accepted: # TODO: Dodaj automatyczną aktualizacje
            self.ui.pushButton_update_application.setEnabled(False)
            logger.debug("[UpdateDialog] The user selected 'Yes'. Updating the app...")

            msg = QMessageBox(self)
            msg.setWindowTitle(QCoreApplication.translate("MainWindow", "DesktopPet_v3", None))
            msg.setText(QCoreApplication.translate("UpdateDialog", "Automatic update has not been implemented yet", None))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
        else:
            logger.debug("[UpdateDialog] The user selected 'No' or closed the window.")

def run_app(conn, shared_data, log_queue) -> None:
    """Entry point for the dashboard process"""
    global logger
    logger = setup_process_logger("dashboard", log_queue)
    logger.info("Starting the DASHBOARD process...")

    app = QApplication(sys.argv)

    translator = Translator(shared_data.settings["language"])

    window = MainWindow(conn, shared_data, translator)
    # window.show() # By default we want to hide the window

    # Creating a tray icon
    tray = QSystemTrayIcon(QIcon(str(config.RESOURCE_DIR / "icon.ico")), app)
    menu = QMenu()
    show_action = menu.addAction("Show Panel")
    translator.tr(lambda: show_action.setText(QCoreApplication.translate("tray-icon", "Show Panel", None)))
    show_action.triggered.connect(window._show_and_focus_window)

    def _show_info_tab() -> None:
        window._show_and_focus_window()
        window.ui.tabWidget.setCurrentWidget(window.ui.tab_info)
    
    menu.addSeparator()
    about_action = menu.addAction("About")
    translator.tr(lambda: about_action.setText(QCoreApplication.translate("tray-icon", "About", None)))
    about_action.triggered.connect(_show_info_tab)

    menu.addSeparator()
    quit_action = menu.addAction("Close")
    translator.tr(lambda: quit_action.setText(QCoreApplication.translate("tray-icon", "Close", None)))
    quit_action.triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.show()

    app.aboutToQuit.connect(keyboard.unhook_all)

    sys.exit(app.exec())
