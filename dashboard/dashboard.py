import sys
from dataclasses import dataclass
from pathlib import Path
import json
import winreg
from typing import Callable
import requests
import time
from datetime import datetime
from threading import Thread

import keyboard
from PySide6.QtCore import (
    Qt, QCoreApplication, Signal,
    QLocale, QSize, QEvent,
    QTimer, QUrl
)
from PySide6.QtWidgets import (
    QApplication, QListWidgetItem, QMenu,
    QMessageBox, QMainWindow, QSystemTrayIcon,
    QDialog, QLabel, QPushButton, 
    QAbstractItemView, QInputDialog, QCheckBox
)
from PySide6.QtGui import QIcon, QPixmap, QDesktopServices, QGuiApplication

import config
import logger
from desktop.mods_manager import Mod, Entity
from dashboard.objects_editor import MainWindow as ObjectsEditorWindow
from dashboard.translator import Translator, replace_format
from dashboard.ui.ui_main_window import Ui_MainWindow
from dashboard.widgets.shortcut_edit import HotkeyDialog
from dashboard.widgets.mod_row import Mod_row
from dashboard.widgets.update_dialog import UpdateDialog
from dashboard.widgets.category_sep import CategorySeparator
from dashboard.widgets.saved_mods_dialog import SavedModsListDialog

MODS_DIR = config.APP_DIR / "Mods"

log = logger.get_logger("dashboard")

@dataclass
class HotkeyBinding:
    """Stores widgets for keyboard shortcuts"""
    label_shortcut: QLabel
    button_set: QPushButton
    button_remove: QPushButton
    callback: Callable

class MainWindow(QMainWindow):
    """Main control panel window for application"""

    exit_requested = Signal() # Used only for keyboard shortcuts, so I don't get the "Terminating process DASHBOARD..." message
    translate = QCoreApplication.translate

    def __init__(self, conn, shared_data, translator):
        super().__init__()
        
        self.conn = conn
        self.shared_data = shared_data
        self.translator = translator

        self.ui = Ui_MainWindow()
        self.ui.setup_ui(self)
        if self.shared_data.settings["window_geometry"]["restore"]:
            self.restore_window_geometry()

        self.setWindowIcon(QIcon(str(config.RESOURCE_DIR / "icon.ico")))

        self.hwnd_self = int(self.winId())
        self.editor_window: ObjectsEditorWindow | None = None
        self._active_mods_baseline: list[str] = []
        self._pending_active_mods: list[str] = []
        self._category_header_items: list[tuple[QListWidgetItem, CategorySeparator]] = []
        
        self._setup_hotkeys()

        self.setup_connections()

        self.retranslate_ui()

        self.exit_requested.connect(self.close_app)

        # Timer
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.tick)
        self.refresh_timer.start(1000)

    # Appearance and functionality
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

        # > Appearance
        self.ui.checkBox_restore_window_geometry.toggled.connect(self._on_restore_window_geometry_toggle)
        self.ui.checkBox_restore_window_geometry.setChecked(self.shared_data.settings["window_geometry"]["restore"])
        
        # > Entities
        self.ui.pushButton_open_objects_editor.clicked.connect(self.open_object_editor)

        for category in self.hotkeys_widgets:
            for key in self.hotkeys_widgets[category]:
                self.hotkeys_widgets[category][key].button_set.clicked.connect(lambda e, category=category, key=key: self._set_hotkey(category, key))
                self.hotkeys_widgets[category][key].button_remove.clicked.connect(lambda e, category=category, key=key: self._remove_hotkey(category, key))
        
        # > System
        self.ui.checkBox_check_for_updates.setChecked(self.shared_data.settings["check_for_updates"])
        self.ui.checkBox_check_for_updates.toggled.connect(self._on_check_for_updates_toggle)

        self.ui.checkBox_autostart.setChecked(self.shared_data.settings["autostart"])
        is_executable = getattr(sys, 'frozen', False)
        self.ui.checkBox_autostart.setEnabled(is_executable)
        if not is_executable:
            self.ui.checkBox_autostart.setToolTip(self.translate("MainWindow", "Autostart is only available for the packaged application, not for the script being run.", None))
        self.ui.checkBox_autostart.toggled.connect(self._on_autostart_toggle)

        self.ui.checkBox_show_window_on_startup.setChecked(self.shared_data.settings["check_for_updates"])
        self.ui.checkBox_show_window_on_startup.toggled.connect(self._on_show_window_on_startup_toggle)
        self.ui.checkBox_show_window_on_startup.setEnabled(self.ui.checkBox_autostart.isChecked())
        
        # > Advanced
        self.ui.checkBox_debug_mode.setChecked(self.shared_data.settings["debug"]["active"])
        self.ui.checkBox_debug_mode.toggled.connect(self.update_debug_visibility)

        self.ui.checkBox_hitboxes_overlay.setChecked(self.shared_data.settings["debug"]["hitbox_overlay"])
        self.ui.checkBox_hitboxes_overlay.toggled.connect(self.update_debug_visibility)

        self.ui.checkBox_debug_information_window.setChecked(self.shared_data.settings["debug"]["debug_window"])
        self.ui.checkBox_debug_information_window.toggled.connect(self.update_debug_visibility)

        self.ui.checkBox_debug_console.setChecked(self.shared_data.settings["debug"]["console"])
        self.ui.checkBox_debug_console.toggled.connect(self.update_debug_visibility)

        self.update_debug_check_states()

        self.ui.pushButton_open_app_folder.clicked.connect(self.open_app_folder)
        self.ui.pushButton_open_latest_log.clicked.connect(self.open_latest_log)
        
        # === Mods ===
        self.ui.listWidget_mods.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.ui.listWidget_mods.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.ui.listWidget_mods.model().rowsMoved.connect(lambda *_: QTimer.singleShot(0, self._on_mods_reordered))
        self.ui.listWidget_mods.currentRowChanged.connect(self._on_mod_selected)

        self.ui.pushButton_mod_settings.clicked.connect(self._on_mod_settings)
        self.ui.toolButton_mod_browse.clicked.connect(self._on_mod_browse)
        self.ui.pushButton_load_mod_list.clicked.connect(self._on_load_mod_list)
        self.ui.pushButton_save_mod_list.clicked.connect(self._on_save_mod_list)
        self.ui.pushButton_discard_mod_changes.clicked.connect(self._on_discard_changes)
        self.ui.pushButton_save_mod_changes.clicked.connect(self._on_save_changes)
        
        # === Displayed entities ===
        self.ui.listWidget_displayed_entities_list.currentItemChanged.connect(self._on_displayed_entity_selected)
        self.ui.listWidget_displayed_entities_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ui.listWidget_displayed_entities_list.customContextMenuRequested.connect(self._on_displayed_entities_list_context_menu)
        self.ui.toolButton_displayed_entity_browse.clicked.connect(self._on_displayed_entity_browse)
        self.ui.pushButton_kill_selected_entity.clicked.connect(self.kill_selected_entity)
        
        # === Spawnable entities ===
        self.ui.listWidget_spawnable_entities_list.currentItemChanged.connect(self._on_spawnable_entity_selected)
        self.ui.pushButton_spawnable_entity_settings.clicked.connect(self._on_spawnable_entity_settings)
        self.ui.toolButton_spawnable_entity_browse.clicked.connect(self._on_spawnable_entity_browse)
        self.ui.pushButton_add_spawnable_entity.clicked.connect(self._on_add_spawnable_entity)
        
        self.ui.pushButton_kill_all_entities.clicked.connect(self.kill_all_entities)
        self.ui.pushButton_show_all_entities.clicked.connect(self.show_all_entities)
        self.ui.pushButton_hide_all_entities.clicked.connect(self.hide_all_entities)

        # === Info ===
        self.ui.label_app_banner.setPixmap(QPixmap(str(config.RESOURCE_DIR / "Assets" / "images" / "banner.png")))
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
                    log.error(f"[Hotkey] Failed to register '{sequence}': {e}")
            return None
        
        self.hotkeys_widgets = {
            "app": {
                "show": HotkeyBinding(
                    label_shortcut = self.ui.label_show_shortcut_value,
                    button_set = self.ui.pushButton_show_shortcut_set,
                    button_remove = self.ui.pushButton_show_shortcut_remove,
                    callback = self.show_and_focus_window,
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
                    callback = lambda: self.kill_all_entities(),
                ),
                "show all": HotkeyBinding(
                    label_shortcut = self.ui.label_show_all_entities_shortcut_value,
                    button_set = self.ui.pushButton_show_all_entities_shortcut_set,
                    button_remove = self.ui.pushButton_show_all_entities_shortcut_remove,
                    callback = lambda: self.show_all_entities(),
                ),
                "hide all": HotkeyBinding(
                    label_shortcut = self.ui.label_hide_all_entities_shortcut_value,
                    button_set = self.ui.pushButton_hide_all_entities_shortcut_set,
                    button_remove = self.ui.pushButton_hide_all_entities_shortcut_remove,
                    callback = lambda: self.hide_all_entities(),
                ),
                "kill": HotkeyBinding(
                    label_shortcut = self.ui.label_kill_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_kill_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_kill_selected_entity_shortcut_remove,
                    callback = lambda: self.kill_selected_entity(),
                ),
                "show": HotkeyBinding(
                    label_shortcut = self.ui.label_show_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_show_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_show_selected_entity_shortcut_remove,
                    callback = lambda: self.show_selected_entity(),
                ),
                "hide": HotkeyBinding(
                    label_shortcut = self.ui.label_hide_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_hide_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_hide_selected_entity_shortcut_remove,
                    callback = lambda: self.hide_selected_entity(),
                ),
                "teleport": HotkeyBinding(
                    label_shortcut = self.ui.label_teleport_selected_entity_shortcut_value,
                    button_set = self.ui.pushButton_teleport_selected_entity_shortcut_set,
                    button_remove = self.ui.pushButton_teleport_selected_entity_shortcut_remove,
                    callback = lambda: self.teleport_selected_entity(),
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

    def retranslate_ui(self) -> None:
        self.ui.retranslate_ui(self)
        # Settings
        for category in self.hotkeys_widgets:
            for key in self.hotkeys_widgets[category]:
                seq = self.shared_data.settings["hotkeys"][category][key]
                self.hotkeys_widgets[category][key].button_remove.setEnabled(seq is not None)
                if seq:
                    self.hotkeys_widgets[category][key].label_shortcut.setText(seq)
                else:
                    self.translator.tr(lambda category=category, key=key: self.hotkeys_widgets[category][key].label_shortcut.setText(self.translate("MainWindow", "No keyboard shortcut", None)))

        # Mods
        self._update_mods_group_title()

        # List of entities
        self._update_displayed_entities_group_title()

        # Add entity
        self._update_spawnable_entities_group_title()

        # Info
        self.ui.label_app_version.setText(replace_format(self.translate("MainWindow", "version: %1  \u2022  %2", None), config.APP_VERSION, config.APP_VERSION_DATE))
        self.update_label_check_for_updates()

        # Version
        self.ui.label_version.setText(replace_format(self.translate("MainWindow", "Version: %1", None), config.APP_VERSION))

    # Window geometry
    def show_and_focus_window(self) -> None:
        if self.isVisible():
            self.reset_geometry()
            QApplication.alert(self, 1)

        self.show()
        self.raise_()
        self.activateWindow()

    def reset_geometry(self) -> None:
        self.adjustSize()

        screen = QGuiApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()

        frame_geo = self.frameGeometry()
        frame_geo.moveCenter(screen_geometry.center())
        self.move(frame_geo.topLeft())
    
    def save_window_geometry(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()

        settings = self.shared_data.settings
        window_geometry = settings["window_geometry"]
        window_geometry["x"] = self.pos().x()
        window_geometry["y"] = self.pos().y()
        window_geometry["width"] = self.size().width()
        window_geometry["height"] = self.size().height()
        window_geometry["screen_name"] = screen.name()
        self.shared_data.settings = settings
        self.save_settings_state()

    def restore_window_geometry(self) -> None:
        window_geometry = self.shared_data.settings["window_geometry"]
        if not all([window_geometry["width"], window_geometry["height"], window_geometry["x"], window_geometry["y"], window_geometry["screen_name"]]):
            self.reset_geometry()
            return

        self.resize(window_geometry["width"], window_geometry["height"])
        self.move(window_geometry["x"], window_geometry["y"])

        target_screen_name = window_geometry["screen_name"]
        screens = QGuiApplication.screens()
        target_screen = next((s for s in screens if s.name() == target_screen_name), None)
        if target_screen is None:
            target_screen = QGuiApplication.primaryScreen()
        self.windowHandle()
        self.setScreen(target_screen)

    # Window events
    def resizeEvent(self, event):
        self.save_window_geometry()
        super().resizeEvent(event)

    def moveEvent(self, event):
        self.save_window_geometry()
        super().moveEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate_ui()
        super().changeEvent(event)

    def closeEvent(self, event):
        """Hides window instead of closing"""
        event.ignore()
        self.hide()

    def tick(self) -> None:
        self._handle_ipc_commands()

        self.update_label_check_for_updates()

    # IPC commands
    def send_ipc_command(self, msg: list[str]) -> None:
        """Sends message to other processes"""
        log.debug(f"Sent IPC: {msg}")
        self.conn.send(msg)

    def _handle_ipc_commands(self) -> None:
        """Checks messages from other processes"""
        while True:
            if self.conn.poll():
                msg = self.conn.recv()
                log.debug(f"Received IPC: {msg}")
                if msg[0] == "Update_mod_list":
                    log.debug(f"Mods: {self.shared_data.active_mods}")
                    self._active_mods_baseline = list(self.shared_data.settings["active_mods"])
                    self._pending_active_mods = list(self._active_mods_baseline)
                    self._populate_mods_list()
                elif msg[0] == "Update_spawnable_entities_list":
                    log.debug(f"Entities: {self.shared_data.spawnable_entities}")
                    self._populate_spawnable_entities_list()
                elif msg[0] == "Update_displayed_entities":
                    self._populate_displayed_entities_list()
                elif msg[0] == "entity_clicked":
                    self._select_displayed_entity(msg[1])
                else:
                    log.error(f"Unknown command: {msg}")
            else:
                return
    
    # Closing the application
    def close_app(self, restart=False) -> None:
        """Sends a command to close the second process and closes the current one"""
        if restart:
            self.shared_data.restart_requested = True
        self.send_ipc_command(["close_app"])
        QCoreApplication.quit()
    
    def restart_app(self) -> None:
        """Sends a command to close the second process and closes the current one, then restarts the application"""
        self.close_app(restart=True)

    # ================= Mods =================

    def _populate_mods_list(self) -> None:
        self.ui.listWidget_mods.clear()

        active_ids = [mid for mid in self._pending_active_mods if mid in self.shared_data.active_mods]
        active_set = set(active_ids)
        inactive_mods = sorted(
            (mod for mod in self.shared_data.active_mods.values() if mod.id not in active_set),
            key=lambda m: m.name.lower(),
        )
        ordered_mods = [self.shared_data.active_mods[mid] for mid in active_ids] + inactive_mods

        for mod in ordered_mods:
            row_widget = Mod_row()
            row_widget.checkBox.setChecked(mod.id in active_set)
            row_widget.label.setText(mod.name)
            row_widget.checkBox.toggled.connect(lambda checked, mod=mod, checkBox=row_widget.checkBox: self._on_mod_toggled(mod, checkBox))
            row_widget.toolButton.clicked.connect(lambda _=False, m=mod: self._on_mod_menu(m))

            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, mod.id)
            if mod.id in active_set:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsDragEnabled)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)

            self.ui.listWidget_mods.addItem(item)
            self.ui.listWidget_mods.setItemWidget(item, row_widget)

        if self.ui.listWidget_mods.count():
            self.ui.listWidget_mods.setCurrentRow(0)
        self._update_mods_group_title()

    def _update_mods_group_title(self) -> None:
        self.ui.groupBox_mods_list.setTitle(replace_format(self.translate("MainWindow", "Mods (%1)", None), len(self.shared_data.active_mods)))

    # Selected mod
    def _mod_for_row(self, row: int) -> Mod | None:
        item = self.ui.listWidget_mods.item(row)
        if item is None:
            return None
        return self.shared_data.active_mods[item.data(Qt.ItemDataRole.UserRole)]

    def _on_mod_selected(self, row: int) -> None:
        mod = self._mod_for_row(row)
        if mod is None:
            return

        pixmap = QPixmap(str(mod.preview_path)) if mod.preview_path is not None else QPixmap()
        self.ui.label_mod_preview.setPixmap(pixmap)
        self.ui.label_mod_name.setText(mod.name)
        self.ui.label_mod_author.setText(mod.author)
        self.ui.label_mod_version.setText(mod.version)
        self.ui.label_mod_id.setText(mod.id)
        self.ui.label_mod_description.setText(mod.description)

    def _on_mod_toggled(self, mod: Mod, checkbox) -> None:
        if checkbox.isChecked():
            if mod.id not in self.shared_data.settings["trusted_mods"]:
                accepted, dont_ask_again = self._confirm_trust_mod(mod, show_dont_ask_checkbox=True)

                if not accepted:
                    checkbox.blockSignals(True)
                    checkbox.setChecked(False)
                    checkbox.blockSignals(False)
                    return

                self._pending_active_mods.append(mod.id)
                if dont_ask_again:
                    settings = self.shared_data.settings
                    settings["trusted_mods"].append(mod.id)
                    self.shared_data.settings = settings
                    self.save_settings_state()
            else:
                self._pending_active_mods.append(mod.id)
        else:
            self._pending_active_mods.remove(mod.id)

        log.debug(f"[mods] pending: {mod.id} -> {'active' if checkbox.isChecked() else 'inactive'}")
        self._populate_mods_list()
        self._update_mod_changes_ui()

    def _on_mods_reordered(self) -> None:
        self._pending_active_mods = [
            self.ui.listWidget_mods.item(row).data(Qt.ItemDataRole.UserRole)
            for row in range(self.ui.listWidget_mods.count())
            if self.ui.listWidget_mods.item(row).data(Qt.ItemDataRole.UserRole)
            in self._pending_active_mods
        ]
        log.debug(f"[mods] pending order: {self._pending_active_mods}")
        self._populate_mods_list()
        self._update_mod_changes_ui()

    def _update_mod_changes_ui(self) -> None:
        has_changes = self._pending_active_mods != self._active_mods_baseline
        self.ui.pushButton_discard_mod_changes.setEnabled(has_changes)
        self.ui.pushButton_save_mod_changes.setEnabled(has_changes)

    def _on_mod_menu(self, mod: Mod) -> None:
        menu = QMenu(self)
        folder_mod_path_url = QUrl.fromLocalFile(str(MODS_DIR / mod.id))
        menu.addAction(self.translate("MainWindow", "Open folder", None), lambda url=folder_mod_path_url: QDesktopServices.openUrl(url))
        menu.addAction(self.translate("MainWindow", "Delete", None), lambda: print(f"[mods] delete: {mod.name}"))  # TODO: Dodaj funkcjonalność przenoszenia folderu moda do kosza i dialog z pytaniem "Czy na pewno chcesz usunąć moda \"%1\""

        if mod.id in self.shared_data.settings["trusted_mods"]:
            menu.addAction(self.translate("MainWindow", "Revoke trust", None), lambda: self._untrust_mod(mod))
        else:
            menu.addAction(self.translate("MainWindow", "Trust", None), lambda: self._trust_mod(mod))

        menu.exec(self.cursor().pos())

    def _on_mod_browse(self) -> None:
        mod = self._mod_for_row(self.ui.listWidget_mods.currentRow())
        if mod is None:
            QMessageBox.information(self, self.translate("MainWindow", "Mod settings", None), self.translate("MainWindow", "Select a mod first.", None))
            return
        self._on_mod_menu(mod)
    
    def _on_mod_settings(self) -> None:
        mod = self._mod_for_row(self.ui.listWidget_mods.currentRow())
        if mod is None:
            QMessageBox.information(self, self.translate("MainWindow", "Mod settings", None), self.translate("MainWindow", "Select a mod first.", None))
            return
        # TODO: Dodaj wyświetlanie ustawień przesłanych przez API moda
        QMessageBox.information(self, self.translate("MainWindow", "Mod settings", None), self.translate("MainWindow", "TODO: settings for %1", None).replace("%1", mod.name))

    # Trust the mod
    def _confirm_trust_mod(self, mod: Mod, show_dont_ask_checkbox: bool = True) -> tuple[bool, bool]:
        """Shows a warning about trusting a mod. Returns (accepted, dont_ask_again)."""
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle(self.translate("TrustModDialog", "Security Warning", None))
        msg_box.setText(replace_format(self.translate("TrustModDialog", "This mod \"%1\" may contain malware. Are you sure you want to trust it?", None), mod.id))
        msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg_box.setDefaultButton(QMessageBox.StandardButton.No)

        dont_ask_checkbox = None
        if show_dont_ask_checkbox:
            dont_ask_checkbox = QCheckBox(self.translate("TrustModDialog", "Don't ask me again for this mod", None))
            msg_box.setCheckBox(dont_ask_checkbox)

        accepted = msg_box.exec() == QMessageBox.StandardButton.Yes
        dont_ask_again = dont_ask_checkbox.isChecked() if dont_ask_checkbox else False
        return accepted, dont_ask_again

    def _trust_mod(self, mod: Mod) -> None:
        if mod.id in self.shared_data.settings["trusted_mods"]:
            return

        accepted, _ = self._confirm_trust_mod(mod, show_dont_ask_checkbox=False)
        if not accepted:
            return

        settings = self.shared_data.settings
        settings["trusted_mods"].append(mod.id)
        self.shared_data.settings = settings
        self.save_settings_state()
        log.debug(f"[mods] trusted: {mod.id}")

    def _untrust_mod(self, mod: Mod) -> None:
        if mod.id not in self.shared_data.settings["trusted_mods"]:
            return

        settings = self.shared_data.settings
        settings["trusted_mods"].remove(mod.id)
        self.shared_data.settings = settings
        self.save_settings_state()
        log.debug(f"[mods] untrusted: {mod.id}")

        if mod.id in self._pending_active_mods:
            self._pending_active_mods.remove(mod.id)
            self._populate_mods_list()
            self._update_mod_changes_ui()

    # Loading and saving mod list changes
    def _on_load_mod_list(self) -> None:
        saved_lists = self.shared_data.settings["saved_mods_list"]
        if not saved_lists:
            QMessageBox.information(self,
                self.translate("MainWindow", "Load mod list", None),
                self.translate("MainWindow", "No saved mod lists yet.", None),
            )
            return

        dialog = SavedModsListDialog(saved_lists, parent=self)
        result = dialog.exec()

        if dialog.modified:
            settings = self.shared_data.settings
            settings["saved_mods_list"] = dialog.saved_lists
            self.shared_data.settings = settings
            self.save_settings_state()

        if result == QDialog.DialogCode.Accepted and dialog.selected_name:
            loaded_ids = saved_lists.get(dialog.selected_name, [])
            missing = [mid for mid in loaded_ids if mid not in self.shared_data.active_mods]
            if missing:
                log.warning(f'[mods] Saved list "{dialog.selected_name}" references missing mods: {missing}')

            self._pending_active_mods = [mid for mid in loaded_ids if mid in self.shared_data.active_mods]
            log.debug(f'[mods] Loaded mod list "{dialog.selected_name}": {self._pending_active_mods}')
            self._populate_mods_list()
            self._update_mod_changes_ui()

    def _on_save_mod_list(self) -> None:
        name, ok = QInputDialog.getText(self,
            self.translate("MainWindow", "Save mod list", None),
            self.translate("MainWindow", "List name:", None),
        )
        if not ok or not name.strip():
            return
        name = name.strip()

        settings = self.shared_data.settings

        if name in settings["saved_mods_list"]:
            confirm = QMessageBox.question(self,
                self.translate("MainWindow", "Overwrite mod list", None),
                replace_format(self.translate("MainWindow",'A saved list named "%1" already exists. Overwrite it?',None), name))
            if confirm != QMessageBox.StandardButton.Yes:
                return

        settings["saved_mods_list"][name] = list(self._pending_active_mods)
        self.shared_data.settings = settings
        self.save_settings_state()
        log.debug(f'[mods] Saved mod list "{name}": {settings["saved_mods_list"][name]}')

    def _on_discard_changes(self) -> None:
        self._pending_active_mods = list(self._active_mods_baseline)
        log.debug("[mods] Changes discarded")
        self._populate_mods_list()
        self._update_mod_changes_ui()

    def _on_save_changes(self) -> None:
        settings = self.shared_data.settings
        settings["active_mods"] = list(self._pending_active_mods)
        self.shared_data.settings = settings
        self.save_settings_state()

        self._active_mods_baseline = list(self._pending_active_mods)
        log.debug("[mods] Changes saved")
        self._update_mod_changes_ui()
        self._prompt_restart_required()

    def _prompt_restart_required(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle(self.translate("MainWindow", "Restart required", None))
        msg.setText(self.translate("MainWindow","Mod changes require an application restart to take effect.",None))
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()

        log.info("Restarting application after mod changes...")
        self.restart_app()

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
            with open(config.APP_DIR / "settings.json", "w", encoding="utf-8") as f:
                json.dump(self.shared_data.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, self.translate("MainWindow", "File saving error", None), self.translate("MainWindow", "Failed to save settings: %1", None).replace("%1", str(e)))

    # Language
    def _on_combobox_language_change(self, index) -> None:
        lang_code = self.ui.comboBox_language.itemData(index)
        settings = self.shared_data.settings
        settings["language"] = self.ui.comboBox_language.currentData()
        self.shared_data.settings = settings
        log.debug((lang_code, self.shared_data.settings["language"]))
        self.save_settings_state()
        self.translator.change_language(lang_code)

    # Sound
    def _on_slider_volume_changes(self, value) -> None:
        self.ui.label_volume_percent.setText(f"{value}%")

    def _on_slider_volume_release(self) -> None:
        settings = self.shared_data.settings
        settings["volume"] = self.ui.horizontalSlider_volume.value()
        self.shared_data.settings = settings
        self.save_settings_state()

    # Appearance
    def _on_restore_window_geometry_toggle(self, checked):
        settings = self.shared_data.settings
        settings["window_geometry"]["restore"] = checked
        self.shared_data.settings = settings
        self.save_settings_state()

    # Shortcuts
    def _set_hotkey(self, category: str, key: str) -> None:
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
            QMessageBox.information(self, self.translate("MainWindow", "Success", None), self.translate("MainWindow", "Assigned '%1'.", None).replace("%1", seq))

    def _remove_hotkey(self, category: str, key) -> None:
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

    # System
    def _on_check_for_updates_toggle(self, checked) -> None:
        settings = self.shared_data.settings
        settings["check_for_updates"] = self.ui.checkBox_check_for_updates.isChecked()
        self.shared_data.settings = settings
        self.save_settings_state()

    def _on_autostart_toggle(self, checked) -> None:
        """Toggles application autostart in Windows registry"""
        self.ui.checkBox_show_window_on_startup.setEnabled(checked)
        
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

        if getattr(sys, 'frozen', False): # Jeśli program jest spakowany do .exe
            cmd = f'"{sys.executable}" --autostart'
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
            QMessageBox.warning(self, self.translate("MainWindow", "Registry error", None), self.translate("MainWindow", "Failed to change autostart setting:\n%1", None).replace("%1", str(e)))

        settings = self.shared_data.settings
        settings["autostart"] = self.ui.checkBox_autostart.isChecked()
        self.shared_data.settings = settings
        self.save_settings_state()
    
    def _on_show_window_on_startup_toggle(self, checked) -> None:
        settings = self.shared_data.settings
        settings["show_on_autostart"] = checked
        self.shared_data.settings = settings
        self.save_settings_state()

    # Advanced
    def update_debug_check_states(self) -> None:
        """Updates enabled/disabled state of debug checkboxes"""
        checked = self.ui.checkBox_debug_mode.isChecked()
        self.ui.checkBox_hitboxes_overlay.setEnabled(checked)
        self.ui.checkBox_debug_information_window.setEnabled(checked)
        self.ui.checkBox_debug_console.setEnabled(checked)

    def update_debug_visibility(self, checked: bool | None=None) -> None:
        """Updates visibility of debug overlays"""
        self.update_debug_check_states()

        settings = self.shared_data.settings
        settings["debug"]["active"] = self.ui.checkBox_debug_mode.isChecked()
        settings["debug"]["hitbox_overlay"] = self.ui.checkBox_hitboxes_overlay.isChecked()
        settings["debug"]["debug_window"] = self.ui.checkBox_debug_information_window.isChecked()
        settings["debug"]["console"] = self.ui.checkBox_debug_console.isChecked()
        self.shared_data.settings = settings
        self.save_settings_state()

        self.send_ipc_command(["toggle_debug"])

    def open_app_folder(self) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(config.APP_DIR)))

    def open_latest_log(self) -> None:
        log_files = sorted((config.APP_DIR / "logs").glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if log_files:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(log_files[0])))

    # ================= OBJECTS EDITOR =================

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

    def _on_editor_window_closed(self) -> None:
        self.editor_window = None
        self.translator.delete_calls_from_owner("dashboard.object_editor")

    # ================= DISPLAYED ENTITIES LIST =================

    def _populate_displayed_entities_list(self) -> None:
        list_widget = self.ui.listWidget_displayed_entities_list
        list_widget.clear()

        icon_size: int = list_widget.iconSize().width()

        for unique_id, entity_id in self.shared_data.displayed_entities.items():
            entity = self.shared_data.spawnable_entities[entity_id]
            pixmap = self._make_square_pixmap(entity.preview_path, icon_size)

            item = QListWidgetItem(QIcon(pixmap), entity.name)
            item.setData(Qt.ItemDataRole.UserRole, unique_id)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            item.setSizeHint(QSize(88, 96))

            list_widget.addItem(item)

        if list_widget.count():
            list_widget.setCurrentRow(0)
        self._update_displayed_entities_group_title()

    def _update_displayed_entities_group_title(self) -> None:
        self.ui.groupBox_displayed_entities_list.setTitle(replace_format(self.translate("MainWindow", "Entities (%1)", None), len(self.shared_data.displayed_entities)))

    # Selected entity
    def _displayed_entity_for_row(self, row: int) -> Entity | None:
        item = self.ui.listWidget_displayed_entities_list.item(row)
        if item is None:
            return None
        unique_id = item.data(Qt.ItemDataRole.UserRole)
        entity_id = self.shared_data.displayed_entities[unique_id]
        return self.shared_data.spawnable_entities[entity_id]

    def _on_displayed_entity_selected(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        unique_id = current.data(Qt.ItemDataRole.UserRole)
        entity_id = self.shared_data.displayed_entities.get(unique_id)
        if entity_id is None:
            self.ui.label_displayed_entity_preview.setPixmap(QPixmap())
            self.ui.label_displayed_entity_name.setText(self.translate("MainWindow", "EntityName", None))
            self.ui.label_displayed_entity_mod_name.setText(self.translate("MainWindow", "unknown", None))
            self.ui.label_displayed_entity_mod_id.setText(self.translate("MainWindow", "unknown", None))
            self.ui.label_displayed_entity_id.setText(self.translate("MainWindow", "unknown", None))
            self.ui.label_displayed_entity_description.setText(self.translate("MainWindow", "No description available.", None))
        else:
            entity = self.shared_data.spawnable_entities[entity_id]
            mod = self.shared_data.active_mods[entity.mod_id]
    
            pixmap = QPixmap(str(entity.preview_path)) if entity.preview_path is not None else QPixmap()
            self.ui.label_displayed_entity_preview.setPixmap(pixmap)
            self.ui.label_displayed_entity_name.setText(entity.name)
            self.ui.label_displayed_entity_mod_name.setText(mod.name)
            self.ui.label_displayed_entity_mod_id.setText(entity.mod_id)
            self.ui.label_displayed_entity_id.setText(entity.id)
            self.ui.label_displayed_entity_description.setText(entity.description)

    def _on_displayed_entity_menu(self, unique_id: str) -> None:
        menu = QMenu(self)
        menu.addAction(self.translate("MainWindow", "Delete", None), lambda: self.kill_entity(unique_id))
        # TODO: Dodaj akcję / polecenie do pokazywania i ukrywania entity
        # if True:
        #     menu.addAction(self.translate("MainWindow", "Show", None), lambda: self.show_entity(unique_id))
        # else:
        #     menu.addAction(self.translate("MainWindow", "Hide", None), lambda: self.hide_entity(unique_id))
        menu.addAction(self.translate("MainWindow", "Teleport", None), lambda: self.teleport_entity(unique_id))
        menu.exec(self.cursor().pos())

    def _on_displayed_entity_browse(self) -> None:
        item = self.ui.listWidget_displayed_entities_list.currentItem()
        if item is None:
            QMessageBox.information(self, self.translate("MainWindow", "Entity", None), self.translate("MainWindow", "Select an entity first.", None))
            return
        self._on_displayed_entity_menu(item.data(Qt.ItemDataRole.UserRole))

    def _on_displayed_entities_list_context_menu(self, pos) -> None:
        list_widget = self.ui.listWidget_displayed_entities_list
        item = list_widget.itemAt(pos)
        if item is None:
            return
        list_widget.setCurrentItem(item)
        self._on_displayed_entity_menu(item.data(Qt.ItemDataRole.UserRole))

    def _current_displayed_entity_id(self) -> str | None:
        item = self.ui.listWidget_displayed_entities_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _select_displayed_entity(self, unique_id: str) -> None:
        list_widget = self.ui.listWidget_displayed_entities_list
        for row in range(list_widget.count()):
            item = list_widget.item(row)
            if item.data(Qt.ItemDataRole.UserRole) == unique_id:
                list_widget.setCurrentItem(item)
                return

    # Selected entity actions
    def kill_selected_entity(self) -> None:
        unique_id = self._current_displayed_entity_id()
        if unique_id is not None:
            self.kill_entity(unique_id)

    def show_selected_entity(self) -> None:
        unique_id = self._current_displayed_entity_id()
        if unique_id is not None:
            self.show_entity(unique_id)

    def hide_selected_entity(self) -> None:
        unique_id = self._current_displayed_entity_id()
        if unique_id is not None:
            self.hide_entity(unique_id)

    def teleport_selected_entity(self) -> None:
        unique_id = self._current_displayed_entity_id()
        if unique_id is not None:
            self.teleport_entity(unique_id)

    # Selected entity commands
    def kill_all_entities(self) -> None:
        """Removes all spawned entities from the world"""
        self.send_ipc_command(["kill_all_entities"])

    def show_all_entities(self):
        self.send_ipc_command(["show_all_entities"])

    def hide_all_entities(self):
        self.send_ipc_command(["hide_all_entities"])

    def kill_entity(self, unique_id: str) -> None:
        """Removes a specific displayed entity"""
        self.send_ipc_command(["kill_entity", unique_id])

    def show_entity(self, unique_id: str) -> None:
        self.send_ipc_command(["show_entity", unique_id])

    def hide_entity(self, unique_id: str) -> None:
        self.send_ipc_command(["hide_entity", unique_id])

    def teleport_entity(self, unique_id: str) -> None:
        self.send_ipc_command(["teleport_entity", unique_id])
    
    # ================= SPAWNABLE ENTITIES LIST =================

    def _make_square_pixmap(self, path: Path | None, size: int) -> QPixmap:
        """Loads image and crops it to a size x size square (center-crop)."""
        src = QPixmap(str(path)) if path is not None else QPixmap()
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

    def _populate_spawnable_entities_list(self) -> None:
        list_widget = self.ui.listWidget_spawnable_entities_list
        list_widget.clear()
        list_widget.setUniformItemSizes(False)
        list_widget.setGridSize(QSize())

        icon_size: int = list_widget.iconSize().width()

        self._category_header_items.clear()

        entities_by_category: dict[str, list[Entity]] = {}
        for entity in self.shared_data.spawnable_entities.values():
            entities_by_category.setdefault(self.shared_data.active_mods[entity.mod_id].name, []).append(entity)

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
                item.setData(Qt.ItemDataRole.UserRole, f"{entity.mod_id}:{entity.id}")
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
                item.setSizeHint(QSize(88, 96))
                list_widget.addItem(item)

        self._update_category_header_widths()

        for row in range(list_widget.count()):
            item = list_widget.item(row)
            if item.data(Qt.ItemDataRole.UserRole) is not None:
                list_widget.setCurrentItem(item)
                break

        self._update_spawnable_entities_group_title()
    
    def _update_spawnable_entities_group_title(self) -> None:
        self.ui.groupBox_spawnable_entities.setTitle(replace_format(self.translate("MainWindow", "Entities (%1)", None), len(self.shared_data.spawnable_entities)))

    def _update_category_header_widths(self) -> None:
        """Stretches category separators in the "Add" entity list to the current viewport width"""
        list_width = self.ui.listWidget_spawnable_entities_list.viewport().width()
        for header_item, header_widget in self._category_header_items:
            header_item.setSizeHint(QSize(list_width, header_widget.sizeHint().height()))

    # Selected entity
    def _spawnable_entity_for_row(self, row: int) -> Entity | None:
        item = self.ui.listWidget_spawnable_entities_list.item(row)
        if item is None:
            return None
        return self.shared_data.spawnable_entities[item.data(Qt.ItemDataRole.UserRole)]

    def _on_spawnable_entity_selected(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if current is None:
            return
        mod_and_entity_id = current.data(Qt.ItemDataRole.UserRole)
        if mod_and_entity_id is None:
            return  # ignore focus on category separator, not an actual entity

        entity = self.shared_data.spawnable_entities[mod_and_entity_id]
        mod = self.shared_data.active_mods[entity.mod_id]

        pixmap = QPixmap(str(entity.preview_path)) if entity.preview_path is not None else QPixmap()
        self.ui.label_spawnable_entity_preview.setPixmap(pixmap)
        self.ui.label_spawnable_entity_name.setText(entity.name)
        self.ui.label_spawnable_entity_mod_name.setText(mod.name)
        self.ui.label_spawnable_entity_mod_id.setText(entity.mod_id)
        self.ui.label_spawnable_entity_id.setText(entity.id)
        self.ui.label_spawnable_entity_description.setText(entity.description)
    
    def _on_spawnable_entity_settings(self):
        entity = self._spawnable_entity_for_row(self.ui.listWidget_spawnable_entities_list.currentRow())
        if entity is None:
            QMessageBox.information(self, self.translate("MainWindow", "Entity settings", None), self.translate("MainWindow", "Select a entity first.", None))
            return
        # TODO: Dodaj wyświetlanie ustawień przesłanych przez API moda
        QMessageBox.information(self, self.translate("MainWindow", "Entity settings", None), self.translate("MainWindow", "TODO: settings for %1", None).replace("%1", entity.name))
    
    def _on_spawnable_entity_menu(self, entity: Entity) -> None:
        menu = QMenu(self)

        menu.exec(self.cursor().pos())
    
    def _on_spawnable_entity_browse(self):
        entity = self._spawnable_entity_for_row(self.ui.listWidget_spawnable_entities_list.currentRow())
        if entity is None:
            QMessageBox.information(self, self.translate("MainWindow", "Entity settings", None), self.translate("MainWindow", "Select a entity first.", None))
            return
        self._on_spawnable_entity_menu(entity)
    
    def _on_add_spawnable_entity(self):
        entity = self._spawnable_entity_for_row(self.ui.listWidget_spawnable_entities_list.currentRow())
        if entity is None:
            QMessageBox.information(self, self.translate("MainWindow", "Entity settings", None), self.translate("MainWindow", "Select a entity first.", None))
            return
        self.send_ipc_command(["spawn_entity", entity.mod_id, entity.id])
    
    # ================= INFO =================

    def get_latest_release(self) -> dict | int:
        """Returns information about the latest release as a dictionary or status_code if an error is encountered"""
        url = f"https://api.github.com/repos/{config.APP_AUTHOR}/{config.REPO_NAME}/releases/latest"
        headers = {"User-Agent": "Python-Script"}

        try:
            response = requests.get(url, headers=headers, timeout=5)

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
        except requests.exceptions.RequestException as e:
            log.error(f"Network error while checking updates: {e}")
            return -1

    def update_label_check_for_updates(self) -> None:
        now = time.time()

        # label update information status
        if isinstance(self.latest_release_info, dict):
            if config.APP_VERSION != self.latest_release_info["version"]:
                self.ui.label_check_for_updates.setText(replace_format(self.translate("MainWindow", "New update \"%1\" from %2 available!", None), self.latest_release_info["version"], self.latest_release_info["published_at"]))
                self.ui.pushButton_update_application.setEnabled(True)
            else:
                self.ui.label_check_for_updates.setText(self.translate("MainWindow", "The application version is up to date", None))
        elif isinstance(self.latest_release_info, int):
            if self.latest_release_info == 404:
                self.ui.label_check_for_updates.setText(self.translate("MainWindow", "Repository not found or no versions published.", None))
            elif self.latest_release_info == -1:
                self.ui.label_check_for_updates.setText(self.translate("MainWindow","Network error. Check your internet connection.",None))
            else:
                self.ui.label_check_for_updates.setText(replace_format(self.translate("MainWindow", "Error: %1", None), self.latest_release_info))
        elif self.latest_release_info is None:
            if self.last_time_checked is None or now > self.last_time_checked + self.update_check_cooldown:
                self.ui.label_check_for_updates.setText(self.translate("MainWindow", "The version has not been checked yet", None))
            else:
                self.ui.label_check_for_updates.setText(self.translate("MainWindow", "Checking for updates...", None))
        else:
            raise Exception("This shouldn't have happened!")
        
        # button "Check for updates"
        if not self.ui.pushButton_check_for_updates.isEnabled() and (self.last_time_checked is None or now > self.last_time_checked + self.update_check_cooldown):
            self.ui.pushButton_check_for_updates.setEnabled(True)

        # label 0 seconds have passed or try again in 0 seconds
        if self.last_time_checked is not None and now < self.last_time_checked + self.update_check_cooldown:
            self.ui.label_check_for_updates_time.setVisible(True)
            if self.latest_release_info is None:
                self.ui.label_check_for_updates_time.setText(replace_format(self.translate("MainWindow", "(%1s)", None), str(round(now - self.last_time_checked))))
            else:
                self.ui.label_check_for_updates_time.setText(replace_format(self.translate("MainWindow", "(%1s)", None), str(max(0, round(self.last_time_checked + self.update_check_cooldown - now)))))
        else:
            self.ui.label_check_for_updates_time.setVisible(False)

    def _worker_check_for_updates(self) -> None:
        self.latest_release_info = self.get_latest_release()

        self.last_time_checked = time.time()
        if isinstance(self.latest_release_info, int):
            self.update_check_cooldown = 60
        else:
            self.update_check_cooldown = 120

        self.update_label_check_for_updates()
        log.debug(self.ui.label_check_for_updates.text())

    def _on_check_for_updates(self) -> None:
        self.last_time_checked = time.time()
        self.update_check_cooldown = 120
        self.ui.pushButton_check_for_updates.setEnabled(False)
        self.latest_release_info = None

        log.debug("Checking for updates...")
        self.update_label_check_for_updates()

        thread = Thread(target=self._worker_check_for_updates, daemon=True)
        thread.start()

    def on_click_update(self) -> None:
        if not isinstance(self.latest_release_info, dict):
            raise Exception("This shouldn't have happened!")
        new_version = self.latest_release_info["version"]
        new_version_date = self.latest_release_info["published_at"]
        dialog = UpdateDialog(new_version, new_version_date, parent=self)
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted: # TODO: Dodaj automatyczną aktualizacje
            self.ui.pushButton_update_application.setEnabled(False)
            log.debug("[UpdateDialog] The user selected 'Yes'. Updating the app...")

            msg = QMessageBox(self)
            msg.setWindowTitle(QCoreApplication.translate("MainWindow", "DesktopPet_v3", None))
            msg.setText(QCoreApplication.translate("UpdateDialog", "Automatic update has not been implemented yet", None))
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()
        else:
            log.debug("[UpdateDialog] The user selected 'No' or closed the window.")

def run_app(conn, shared_data, log_queue) -> None:
    """Entry point for the dashboard process"""
    logger.init_child(log_queue)
    log.info("Starting the DASHBOARD process...")

    app = QApplication(sys.argv)

    translator = Translator(shared_data.settings["language"])

    window = MainWindow(conn, shared_data, translator)
    if shared_data.restarted or not shared_data.args.autostart or (shared_data.args.autostart and shared_data.settings["show_on_autostart"]):
        window.show()

    # Creating a tray icon
    tray = QSystemTrayIcon(QIcon(str(config.RESOURCE_DIR / "icon.ico")), app)
    
    def _show_info_tab() -> None:
        window.show_and_focus_window()
        window.ui.tabWidget.setCurrentWidget(window.ui.tab_info)
    
    menu = QMenu()
    show_action = menu.addAction("Show Panel")
    translator.tr(lambda: show_action.setText(QCoreApplication.translate("tray-icon", "Show Panel", None)))
    show_action.triggered.connect(window.show_and_focus_window)
    
    menu.addSeparator()
    about_action = menu.addAction("About")
    translator.tr(lambda: about_action.setText(QCoreApplication.translate("tray-icon", "About", None)))
    about_action.triggered.connect(_show_info_tab)

    menu.addSeparator()
    quit_action = menu.addAction("Close")
    translator.tr(lambda: quit_action.setText(QCoreApplication.translate("tray-icon", "Close", None)))
    quit_action.triggered.connect(window.close_app)
    tray.setContextMenu(menu)
    tray.show()

    app.aboutToQuit.connect(keyboard.unhook_all)

    sys.exit(app.exec())
