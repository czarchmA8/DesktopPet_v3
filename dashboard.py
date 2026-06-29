import sys
import os
import json
from PyQt6 import QtWidgets, QtCore, QtGui
import winreg
import keyboard
import win32api, win32con, ctypes
from ctypes import wintypes
import logging

from logger_setup import setup_process_logger

logger: logging.Logger = None

class StatRow(QtWidgets.QWidget):
    '''Widget displaying a statistic with label, progress bar, and percentage'''
    def __init__(self, label_text, icon_char, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Ikona (Emoji lub obrazek)
        self.icon_label = QtWidgets.QLabel(icon_char)
        self.icon_label.setFixedWidth(30)
        self.icon_label.setStyleSheet("font-size: 18px;")

        # Nazwa
        self.name_label = QtWidgets.QLabel(label_text)
        self.name_label.setFixedWidth(100)

        # Pasek postępu
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(12)

        # Wartość %
        self.value_label = QtWidgets.QLabel("100%")
        self.value_label.setFixedWidth(40)
        self.value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.value_label)

    def update_value(self, value: int) -> None:
        '''Updates the statistic value and progress bar color'''
        val = int(max(0, min(100, value)))
        self.progress.setValue(val)
        self.value_label.setText(f"{val}%")

        # Zmiana koloru paska w zależności od wartości
        if val > 70:
            color = "#4CAF50"  # Zielony
        elif val > 30:
            color = "#FFC107"  # Żółty
        else:
            color = "#F44336"  # Czerwony

        self.progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #555;
                border-radius: 5px;
                background-color: #333;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 5px;
            }}
        """)

class CustomKeySequenceEdit(QtWidgets.QLineEdit):
    '''Custom QLineEdit for capturing keyboard hotkey sequences'''
    keySequenceChanged = QtCore.pyqtSignal(QtGui.QKeySequence)

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    # prototypy funkcji
    user32.MapVirtualKeyExW.restype = wintypes.UINT
    user32.MapVirtualKeyExW.argtypes = (wintypes.UINT, wintypes.UINT, wintypes.HKL)

    user32.GetKeyboardLayout.restype = wintypes.HKL
    user32.GetKeyboardLayout.argtypes = (wintypes.DWORD,)

    user32.GetKeyNameTextW.restype = ctypes.c_int
    user32.GetKeyNameTextW.argtypes = (wintypes.LPARAM, wintypes.LPWSTR, ctypes.c_int)

    def get_key_name(self, vk_code: int = None, scan_code: int = None) -> str | None:
        '''Gets the display name of a key from virtual key code'''
        if vk_code is None and scan_code is None:
            raise Exception()

        BUFFER_LEN = 50

        # 1. jeśli scan_code nie podano, VK → scan code
        if scan_code is None:
            scan_code = self.user32.MapVirtualKeyExW(
                vk_code,
                4,  # 0=MAPVK_VK_TO_VSC, 4=MAPVK_VK_TO_VSC_EX
                self.user32.GetKeyboardLayout(0)
            )

        if not scan_code:
            return None

        # 2. Wyodrębnienie faktu, czy to klawisz rozszerzony (przedrostek 0xE000)
        # oraz samego bazowego kodu skanowania (dolne 8 bitów)
        is_extended = (scan_code & 0xFF00) == 0xE000
        base_scan_code = scan_code & 0xFF

        # 3. Budujemy lParam jak w WM_KEYDOWN (kod skanowania na bitach 16-23)
        lparam = (base_scan_code << 16) | 0x1

        # 4. Extended keys - poprawnie ustawiamy bit 24
        if is_extended:
            lparam |= 0x01000000

        # (Opcjonalnie) Ręczne wymuszenie bitu rozszerzonego dla pewności
        # LWIN = 0x5B, RWIN = 0x5C, APPS = 0x5D
        # VK_PRIOR = 0x21
        # VK_HELP = 0x2F
        # if (VK_PRIOR <= vk_code <= VK_HELP) or vk_code in (0x5B, 0x5C, 0x5D):
        #      lparam |= 0x01000000

        # 5. Pobranie nazwy
        buffer = ctypes.create_unicode_buffer(BUFFER_LEN + 1)
        result = self.user32.GetKeyNameTextW(lparam, buffer, BUFFER_LEN)

        if result:
            return buffer.value

        return None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sequence = QtGui.QKeySequence()
        self.setPlaceholderText("Naciśnij kombinację klawiszy...")
        self.keys_pressed = {}
        self.clear_keys_pressed = False

        # print("Wyświetlanie zmian w nazywaniu klawiszy:")
        # print(f"Esc = {self.get_key_name(27)}")
        # print(f"F1 = {self.get_key_name(112)}")
        # print(f"` = {self.get_key_name(192)}")
        # print(f"1 = {self.get_key_name(49)}")
        # print(f"Caps Lock = {self.get_key_name(20)}")
        # print(f"Shift = {self.get_key_name(16)}")
        # print(f"Space = {self.get_key_name(32)}")
        # print(f"Insert = {self.get_key_name(45)}")
        # print(f"Num 7 = {self.get_key_name(103)}")
        # print(f"Pause = {self.get_key_name(144)}")
        # print(f"Home = {self.get_key_name(36)}")
        # print(f"Up = {self.get_key_name(38)}")

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        '''Handles key press events for hotkey capture'''
        if event.isAutoRepeat():
            return

        if self.clear_keys_pressed:
            self.keys_pressed.clear()
            self.clear_keys_pressed = False

        key_int = event.key()
        modifiers_int = event.modifiers().value
        qt_key = key_int | modifiers_int
        self._sequence = QtGui.QKeySequence(qt_key)

        self.keySequenceChanged.emit(self._sequence)

        scan_code = event.nativeScanCode()
        virtual_key = event.nativeVirtualKey()

        # Jakieś stara zamiana która nie ogarniała klawiszy Num i strzałek
        # scan_code = ctypes.windll.user32.MapVirtualKeyExW(vk, 0, ctypes.windll.user32.GetKeyboardLayout(0))
        #
        # lparam = scan_code << 16
        # name_buffer = ctypes.create_unicode_buffer(64)
        # ctypes.windll.user32.GetKeyNameTextW(lparam, name_buffer, ctypes.sizeof(name_buffer))
        # real_key_name = str(name_buffer.value)

        # Zwraca "VK_Control" zamiast "Ctrl"
        # keys = {getattr(win32con, v): v for v in dir(win32con) if v.startswith("VK_")}
        #
        # def get_key_text(key):
        #      return keys.get(key, chr(key))

        real_key_name = self.get_key_name(vk_code=virtual_key, scan_code=scan_code)
        if real_key_name and real_key_name not in self.keys_pressed:
            self.keys_pressed[real_key_name] = virtual_key
        # print(f"scan_code: {scan_code}")
        # print(f"virtual_key: {virtual_key}")
        # print(f"real_key_name: {real_key_name}")
        # print(f"print(\"{real_key_name} = {'{'}self.get_key_name({virtual_key}){'}'}\")")

        # print(self._sequence.toString())
        self.setText(" + ".join(self.keys_pressed))

        self.selectAll()

    def keyReleaseEvent(self, event: QtGui.QKeyEvent):
        '''Handles key release events'''
        if event.isAutoRepeat():
            return
        self.clear_keys_pressed = True

class HotkeyDialog(QtWidgets.QDialog):
    '''Dialog for binding keyboard hotkeys to actions'''
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nagraj skrót klawiszowy")
        self.setFixedSize(300, 150)

        layout = QtWidgets.QVBoxLayout(self)

        self.label = QtWidgets.QLabel("Naciśnij kombinację klawiszy:")
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(self.label)

        self.key_sequence_edit = CustomKeySequenceEdit(self)
        layout.addWidget(self.key_sequence_edit)

        self.final_sequence = ""

        # Przyciski
        btns = QtWidgets.QHBoxLayout()
        self.btn_ok = QtWidgets.QPushButton("OK")
        self.btn_ok.clicked.connect(self.on_accept)

        btn_cancel = QtWidgets.QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)

        btns.addWidget(self.btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def on_accept(self):
        if len(self.key_sequence_edit.keys_pressed) > 0:
            self.final_sequence = "+".join(self.key_sequence_edit.keys_pressed.keys())
            self.accept()

class ControlWindow(QtWidgets.QWidget):
    '''Main control panel window for application'''
    exit_requested = QtCore.pyqtSignal()
    def __init__(self, conn, shared_data):
        super().__init__()
        self.conn = conn
        self.shared_data = shared_data

        def _add_hotkey(sequence, callback):
            """Registers hotkey if sequence is not None/empty, otherwise returns None."""
            if sequence:
                try:
                    return keyboard.add_hotkey(sequence, callback)
                except Exception as e:
                    logger.error(f"[Hotkey] Failed to register '{sequence}': {e}")
            return None

        self.hotkey_callbacks: dict[str, dict] = {
            "app": {
                "show": lambda: (self.show(), self.raise_(), self.activateWindow()),
                "hide": lambda: self.hide(),
                "exit": lambda: self.exit_requested.emit()
            },
            "pet": {
                "show": lambda: self.conn.send(["show_pet"]),
                "hide": lambda: self.conn.send(["hide_pet"]),
                "teleport": lambda: self.conn.send(["teleport_pet"])
            },
            "objects": {
                "remove_all": lambda: self.clear_all_objects()
            }
        }
        hotkeys_settings: dict = shared_data.settings["hotkeys"]
        self.hotkeys: dict[str, dict] = {}
        for category in self.hotkey_callbacks:
            for key in self.hotkey_callbacks[category]:
                self.hotkeys.setdefault(category, {})[key] = _add_hotkey(hotkeys_settings[category][key], self.hotkey_callbacks[category][key])
        self.hotkeys["objects"]["create"] = {
            name: _add_hotkey(hotkeys_settings["objects"]["create"][name], lambda name=name: conn.send(["spawn_object", name]))
            for name in hotkeys_settings["objects"].get("create", {})
            if os.path.exists(os.path.join("Assets", "Objects", name))
        }

        self.setWindowTitle("Panel Sterowania Zwierzątkiem")
        self.resize(500, 600)
        self.setWindowIcon(QtGui.QIcon("icon.ico"))

        self.setStyleSheet("""
            QWidget { background-color: #2b2b2b; color: #ffffff; font-family: Segoe UI, sans-serif; }
            QTabWidget::pane { border: 1px solid #444; }
            QTabBar::tab { background: #3c3c3c; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #505050; font-weight: bold; }
            QPushButton { background-color: #0d6efd; border: none; padding: 8px; border-radius: 4px; }
            QPushButton:hover { background-color: #0b5ed7; }
            QPushButton:pressed { background-color: #0a58ca; }
            QListWidget { background-color: #333; border: 1px solid #555; border-radius: 4px; }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #0d6efd; }
            QSlider::groove:horizontal { border: 1px solid #999; height: 8px; background: #333; margin: 2px 0; border-radius: 4px; }
            QSlider::handle:horizontal { background: #0d6efd; border: 1px solid #5c5c5c; width: 18px; height: 18px; margin: -7px 0; border-radius: 9px; }
            QScrollArea { border: none; background-color: #2b2b2b; }
            QScrollBar:vertical { border: 1px solid #555; background-color: #333; width: 12px; margin: 0px 0px 0px 0px; }
            QScrollBar::handle:vertical { background-color: #0d6efd; border-radius: 6px; min-height: 20px; }
            QScrollBar::handle:vertical:hover { background-color: #0b5ed7; }
            QScrollBar::sub-line:vertical { border: none; background: none; }
            QScrollBar::add-line:vertical { border: none; background: none; }

        """)

        self.hwnd_self = int(self.winId())

        # Główny layout
        main_layout = QtWidgets.QVBoxLayout(self)
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # Zakładki
        self.tab_stats = QtWidgets.QWidget()
        self.tab_settings = QtWidgets.QWidget()
        self.tab_objects = QtWidgets.QWidget()

        self.tabs.addTab(self.tab_stats, "Statystyki")
        self.tabs.addTab(self.tab_settings, "Ustawienia")
        self.tabs.addTab(self.tab_objects, "Obiekty")

        self.lbl_app_hotkeys: dict = None
        self.setup_stats_ui()
        self.setup_settings_ui()
        self.setup_objects_ui()

        # Timer do odświeżania statystyk (co 1s)
        self.stats_timer = QtCore.QTimer(self)
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(1000)

        self.exit_requested.connect(QtCore.QCoreApplication.quit)

        self.version_label = QtWidgets.QLabel("Version 1.0.0", self)
        self.version_label.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 11px; background: transparent;")
        self.version_label.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.version_label.adjustSize()
        self.version_label.move(self.width() - self.version_label.width() - 10, self.height() - self.version_label.height() - 5)

    # ================= STATYSTYKI =================
    def setup_stats_ui(self) -> None:
        '''Sets up the pet statistics display UI tab'''
        layout = QtWidgets.QVBoxLayout(self.tab_stats)

        # Słownik mapujący nazwę pola w klasie Stats na opis i ikonę
        self.stat_widgets = {}
        stats_map = [
            ("fitness", "Kondycja", "💪"),
            ("friendship", "Przyjaźń", "❤️"),
            ("happiness", "Zadowolenie", "😄"),
            ("comfort", "Komfort", "🛋️"),
            ("hunger", "Głód", "🍗"),
            ("thirst", "Pragnienie", "💧"),
            ("energy", "Energia", "⚡"),
            ("cleanliness", "Czystość", "✨"),
            ("warmth", "Ciepło", "🌡️"),
            ("attention", "Uwaga", "👀"),
            ("playfulness", "Zabawa", "⚽"),
        ]

        for attr, name, icon in stats_map:
            row = StatRow(name, icon)
            layout.addWidget(row)
            self.stat_widgets[attr] = row

        layout.addStretch()

    def update_stats(self):
        for attr, widget in self.stat_widgets.items():
            # val = getattr(self.shared_data.pet["stats"], attr)
            val = self.shared_data.pet["stats"][attr]

            widget.update_value(val)

    # ================= USTAWIENIA =================
    def setup_settings_ui(self):
        # Główny layout dla tab_settings
        main_layout = QtWidgets.QVBoxLayout(self.tab_settings)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ScrollArea
        scroll_area = QtWidgets.QScrollArea()
        scroll_area.setWidgetResizable(True)

        # Container widget dla całej zawartości
        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)

        # Głośność
        vol_group = QtWidgets.QGroupBox("Dźwięk")
        vol_layout = QtWidgets.QVBoxLayout()

        lbl_vol = QtWidgets.QLabel("Głośność:")
        self.slider_vol = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider_vol.setRange(0, 100)
        self.slider_vol.setValue(self.shared_data.settings["volume"])
        self.slider_vol.valueChanged.connect(self.save_settings_state)

        self.lbl_vol_pct = QtWidgets.QLabel(f"{self.shared_data.settings['volume']}%")
        self.lbl_vol_pct.setFixedWidth(40)
        self.lbl_vol_pct.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.slider_vol.valueChanged.connect(lambda v: self.lbl_vol_pct.setText(f"{v}%"))

        slider_row = QtWidgets.QHBoxLayout()
        slider_row.addWidget(self.slider_vol)
        slider_row.addWidget(self.lbl_vol_pct)

        vol_layout.addWidget(lbl_vol)
        vol_layout.addLayout(slider_row)
        vol_group.setLayout(vol_layout)
        layout.addWidget(vol_group)

        # System - Autostart
        sys_group = QtWidgets.QGroupBox("System")
        sys_layout = QtWidgets.QVBoxLayout()

        self.check_autostart = QtWidgets.QCheckBox("Uruchamiaj przy starcie systemu")
        self.check_autostart.setChecked(self.shared_data.settings["autostart"])
        self.check_autostart.toggled.connect(self.toggle_autostart)

        # if winreg is None:
        #      self.check_autostart.setEnabled(False)
        #      self.check_autostart.setToolTip("Autostart dostępny tylko na Windows (moduł winreg niedostępny).")

        sys_layout.addWidget(self.check_autostart)
        sys_group.setLayout(sys_layout)
        layout.addWidget(sys_group)

        # Obiekty - skrót do usunięcia wszystkich
        self.lbl_app_hotkeys = {}
        obj_group = QtWidgets.QGroupBox("Obiekty")
        obj_layout = QtWidgets.QVBoxLayout()

        obj_layout.addWidget(QtWidgets.QLabel("Skrót klawiszowy do usunięcia wszystkich obiektów:"))

        category = "objects"
        key = "remove_all"
        h = self.shared_data.settings["hotkeys"]["objects"][key]
        val_lbl = QtWidgets.QLabel(h if h else "Brak")
        val_lbl.setStyleSheet("color: #aaa; font-style: italic;")
        self.lbl_app_hotkeys.setdefault(category, {})[key] = val_lbl

        obj_hk_btns = QtWidgets.QHBoxLayout()
        btn_set_clear_hk = QtWidgets.QPushButton("Ustaw skrót")
        btn_set_clear_hk.clicked.connect(lambda _, c=category, k=key: self.set_app_hotkey(c, k))
        btn_rem_clear_hk = QtWidgets.QPushButton("Usuń skrót")
        btn_rem_clear_hk.clicked.connect(lambda _, c=category, k=key: self.remove_app_hotkey(c, k))
        obj_hk_btns.addWidget(btn_set_clear_hk)
        obj_hk_btns.addWidget(btn_rem_clear_hk)

        obj_layout.addWidget(val_lbl)
        obj_layout.addLayout(obj_hk_btns)
        obj_group.setLayout(obj_layout)
        layout.addWidget(obj_group)

        # Aplikacja - skróty show/hide/exit
        app_group = QtWidgets.QGroupBox("Aplikacja")
        app_layout = QtWidgets.QVBoxLayout()

        app_hotkeys_cfg = [
            ("show",  "Pokaż aplikację"),
            ("hide",  "Ukryj aplikację"),
            ("exit",  "Zamknij aplikację"),
        ]
        category = "app"
        for key, label in app_hotkeys_cfg:
            row_lbl = QtWidgets.QLabel(f"{label}:")
            current = self.shared_data.settings["hotkeys"]["app"][key]
            val_lbl = QtWidgets.QLabel(current if current else "Brak")
            val_lbl.setStyleSheet("color: #aaa; font-style: italic;")
            self.lbl_app_hotkeys.setdefault(category, {})[key] = val_lbl

            btns_row = QtWidgets.QHBoxLayout()
            btn_set = QtWidgets.QPushButton("Ustaw")
            btn_set.clicked.connect(lambda _, c=category, k=key: self.set_app_hotkey(c, k))
            btn_rem = QtWidgets.QPushButton("Usuń")
            btn_rem.clicked.connect(lambda _, c=category, k=key: self.remove_app_hotkey(c, k))
            btns_row.addWidget(btn_set)
            btns_row.addWidget(btn_rem)

            app_layout.addWidget(row_lbl)
            app_layout.addWidget(val_lbl)
            app_layout.addLayout(btns_row)

        app_group.setLayout(app_layout)
        layout.addWidget(app_group)

        # Zwierzątko
        pet_group = QtWidgets.QGroupBox("Zwierzątko")
        pet_layout = QtWidgets.QVBoxLayout()

        pet_hotkeys_cfg = [
            ("show", "Pokaż zwierzątko"),
            ("hide", "Ukryj zwierzątko"),
            ("teleport", "Teleportuj zwierzątko")
        ]
        category = "pet"
        for key, label in pet_hotkeys_cfg:
            row_lbl = QtWidgets.QLabel(f"{label}:")
            current = self.shared_data.settings["hotkeys"][category][key]
            val_lbl = QtWidgets.QLabel(current if current else "Brak")
            val_lbl.setStyleSheet("color: #aaa; font-style: italic;")
            self.lbl_app_hotkeys.setdefault(category, {})[key] = val_lbl

            btns_row = QtWidgets.QHBoxLayout()
            btn_set = QtWidgets.QPushButton("Ustaw")
            btn_set.clicked.connect(lambda _, c=category, k=key: self.set_app_hotkey(c, k))
            btn_rem = QtWidgets.QPushButton("Usuń")
            btn_rem.clicked.connect(lambda _, c=category, k=key: self.remove_app_hotkey(c, k))
            btns_row.addWidget(btn_set)
            btns_row.addWidget(btn_rem)

            pet_layout.addWidget(row_lbl)
            pet_layout.addWidget(val_lbl)
            pet_layout.addLayout(btns_row)

        pet_group.setLayout(pet_layout)
        layout.addWidget(pet_group)

        # Zaawansowane
        advanced_group = QtWidgets.QGroupBox("Zaawansowane")
        advanced_layout = QtWidgets.QVBoxLayout()

        self.check_debug_mode = QtWidgets.QCheckBox("Tryb debugowania")
        self.check_debug_mode.setChecked(self.shared_data.settings["debug"]["active"])
        self.check_debug_mode.toggled.connect(self.update_debug_visibility)
        advanced_layout.addWidget(self.check_debug_mode)

        self.check_hitbox_overlay = QtWidgets.QCheckBox("Wyświetlanie hitbox-ów")
        self.check_hitbox_overlay.setChecked(self.shared_data.settings["debug"]["hitbox_overlay"])
        self.check_hitbox_overlay.toggled.connect(self.update_debug_visibility)
        advanced_layout.addWidget(self.check_hitbox_overlay)

        self.check_debug_window = QtWidgets.QCheckBox("Okno z informacjami")
        self.check_debug_window.setChecked(self.shared_data.settings["debug"]["debug_window"])
        self.check_debug_window.toggled.connect(self.update_debug_visibility)
        advanced_layout.addWidget(self.check_debug_window)

        self._update_debug_check_states()
        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()
        scroll_area.setWidget(container)
        main_layout.addWidget(scroll_area)

    def set_app_hotkey(self, category: str, key: str):
        dialog = HotkeyDialog(self)
        dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
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
            self.hotkeys[category][key] = keyboard.add_hotkey(seq, self.hotkey_callbacks[category][key])
            self.lbl_app_hotkeys[category][key].setText(seq)
            self.save_settings_state()
            QtWidgets.QMessageBox.information(self, "Sukces", f"Przypisano '{seq}'.")

    def remove_app_hotkey(self, category: str, key):
        seq = self.shared_data.settings["hotkeys"][category].get(key)
        if seq:
            keyboard.remove_hotkey(seq)
            settings = self.shared_data.settings
            settings["hotkeys"][category][key] = None
            self.shared_data.settings = settings
            self.lbl_app_hotkeys[category][key].setText("Brak")
            self.save_settings_state()
            QtWidgets.QMessageBox.information(self, "Sukces", "Usunięto skrót.")
        else:
            QtWidgets.QMessageBox.information(self, "Informacja", "Brak przypisanego skrótu.")

    def save_settings_state(self) -> None:
        '''Saves current settings to settings.json'''
        settings = self.shared_data.settings
        settings["volume"] = self.slider_vol.value()
        settings["autostart"] = self.check_autostart.isChecked()
        settings["debug"]["active"] = self.check_debug_mode.isChecked()
        settings["debug"]["hitbox_overlay"] = self.check_hitbox_overlay.isChecked()
        settings["debug"]["debug_window"] = self.check_debug_window.isChecked()
        self.shared_data.settings = settings

        try:
            with open("settings.json", "w", encoding="utf-8") as f:
                json.dump(self.shared_data.settings, f, indent=4, ensure_ascii=False)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Błąd zapisu", f"Nie udało się zapisać ustawień: {e}")

    def toggle_autostart(self, checked) -> None:
        '''Toggles application autostart in Windows registry'''
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "DesktopPet_v3"

        if getattr(sys, 'frozen', False): # Jeśli program jest spakowany do .exe
            cmd = f'"{sys.executable}"'
        else: # Jeśli to surowy skrypt .py
            self.check_autostart.blockSignals(True)
            self.check_autostart.setChecked(False)
            self.check_autostart.blockSignals(False)
            QtWidgets.QMessageBox.information(self, "Autostart niedostępny", "Autostart jest dostępny tylko dla spakowanej aplikacji, a nie dla uruchamianego skryptu.")
            return

            # Dodawanie skryptu do autostartu (porzucone)
            # pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
            # script_path = os.path.abspath(sys.argv[0])
            # # Dodajemy /d, aby Windows odpalił skrypt w jego folderze macierzystym
            # cmd = f'cmd.exe /c "cd /d "{os.path.dirname(script_path)}" && "{pythonw_path}" "{script_path}""'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
            if checked:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            self.check_autostart.blockSignals(True)
            self.check_autostart.setChecked(not checked)
            self.check_autostart.blockSignals(False)
            QtWidgets.QMessageBox.warning(self, "Błąd rejestru", f"Nie udało się zmienić ustawienia autostartu:\n{e}")

        self.save_settings_state()

    def _update_debug_check_states(self):
        '''Updates enabled/disabled state of debug checkboxes'''
        checked = self.check_debug_mode.isChecked()
        self.check_hitbox_overlay.setEnabled(checked)
        self.check_debug_window.setEnabled(checked)

    def update_debug_visibility(self, checked: bool=None):
        '''Updates visibility of debug overlays'''
        self._update_debug_check_states()

        self.save_settings_state()
        self.conn.send(["toggle_debug"])

    # ================= OBIEKTY =================
    def setup_objects_ui(self):
        '''Sets up the interactive objects UI tab'''
        layout = QtWidgets.QVBoxLayout(self.tab_objects)

        # Lista plików
        self.list_objects = QtWidgets.QListWidget()
        self.refresh_objects_list()
        layout.addWidget(self.list_objects)

        # Przyciski
        btn_layout = QtWidgets.QHBoxLayout()

        self.btn_spawn = QtWidgets.QPushButton("Stwórz obiekt (Kursor)")
        self.btn_spawn.setEnabled(False)
        self.btn_spawn.clicked.connect(self.spawn_selected)

        self.btn_hotkey = QtWidgets.QPushButton("Przypisz skrót klawiszowy")
        self.btn_hotkey.setEnabled(False)
        self.btn_hotkey.clicked.connect(self.bind_hotkey)

        self.btn_remove_hotkey = QtWidgets.QPushButton("Usuń skrót")
        self.btn_remove_hotkey.setEnabled(False)
        self.btn_remove_hotkey.clicked.connect(self.remove_hotkey)

        btn_layout.addWidget(self.btn_spawn)
        btn_layout.addWidget(self.btn_hotkey)
        btn_layout.addWidget(self.btn_remove_hotkey)
        layout.addLayout(btn_layout)

        btn_clear_all = QtWidgets.QPushButton("🗑 Usuń wszystkie obiekty")
        btn_clear_all.setStyleSheet("background-color: #c0392b;")
        btn_clear_all.clicked.connect(self.clear_all_objects)
        layout.addWidget(btn_clear_all)

        # Info o aktualnych skrótach
        self.lbl_hotkey_info = QtWidgets.QLabel("Zaznacz obiekt by zobaczyć skrót.")
        self.lbl_hotkey_info.setStyleSheet("color: #888; font-style: italic;")
        layout.addWidget(self.lbl_hotkey_info)

        self.list_objects.itemClicked.connect(self.on_object_selected)

    def remove_hotkey(self) -> None:
        '''Removes hotkey binding from selected object'''
        item = self.list_objects.currentItem()
        if not item:
            QtWidgets.QMessageBox.information(self, "Brak obiektu", "Zaznacz obiekt z listy.")
            return

        filename = item.text()

        settings =  self.shared_data.settings
        if filename in settings["hotkeys"]["objects"]["create"]:
            del settings["hotkeys"]["objects"]["create"][filename]
            del self.hotkeys["objects"]["create"][filename]
            self.shared_data.settings = settings
            self.save_settings_state()
            self.on_object_selected(item)
            QtWidgets.QMessageBox.information(self, "Sukces", f"Usunięto skrót dla '{filename}'")
        else:
            QtWidgets.QMessageBox.information(self, "Informacja", "Ten obiekt nie ma obecnie przypisanego skrótu.")

    def refresh_objects_list(self) -> None:
        '''Refreshes the list of available objects'''
        self.list_objects.clear()
        ASSETS_DIR = os.path.join("Assets", "Objects")
        if os.path.exists(ASSETS_DIR):
            files = [f for f in os.listdir(ASSETS_DIR) if f.lower().endswith(('.png', '.gif', '.jpg'))]
            for f in files:
                icon = QtGui.QIcon(os.path.join(ASSETS_DIR, f))
                item = QtWidgets.QListWidgetItem(icon, f)
                self.list_objects.addItem(item)
        else:
            self.list_objects.addItem("Brak folderu Assets/Objects!")

    def spawn_selected(self) -> None:
        '''Creates selected object at cursor position'''
        item = self.list_objects.currentItem()
        if item:
            self.conn.send(["spawn_object", item.text()])

    def bind_hotkey(self):
        '''Binds keyboard hotkey to object creation'''
        item = self.list_objects.currentItem()
        if not item:
            QtWidgets.QMessageBox.information(self, "Brak obiektu", "Zaznacz obiekt z listy.")
            return

        filename = item.text()
        dialog = HotkeyDialog(self)
        dialog.setWindowModality(QtCore.Qt.WindowModality.WindowModal)
        if dialog.exec():
            seq_str = dialog.final_sequence
            if not seq_str:
                return

            try:
                self.hotkeys["create objects"][filename] = keyboard.add_hotkey(seq_str, lambda name=filename: self.conn.send(["spawn_object", name]))
                settings = self.shared_data.settings
                settings["hotkeys"]["objects"]["create"][filename] = seq_str
                self.shared_data.settings = settings
                self.save_settings_state()
                self.on_object_selected(item)
                QtWidgets.QMessageBox.information(self, "Sukces", f"Przypisano '{seq_str}' do '{filename}'")
            except Exception as e:
                logger.error(f"ERROR: {e}")
                QtWidgets.QMessageBox.information(self, "Błąd", f"Wystąpił problem podczas przypisywania '{seq_str}' do '{filename}'")

    def on_object_selected(self, item):
        '''Handles object selection in list'''
        filename = item.text()
        hotkey = self.shared_data.settings["hotkeys"]["objects"]["create"].get(filename)
        if hotkey:
            self.lbl_hotkey_info.setText(f"Skrót: {hotkey}")
            self.btn_remove_hotkey.setEnabled(True)
        else:
            self.lbl_hotkey_info.setText("Brak przypisanego skrótu.")
            self.btn_remove_hotkey.setEnabled(False)
        self.btn_hotkey.setEnabled(True)
        self.btn_spawn.setEnabled(True)

    def clear_all_objects(self):
        '''Removes all spawned objects from the world'''
        self.conn.send(["clear_all_objects"])

    def closeEvent(self, event):
        '''Hides window instead of closing'''
        event.ignore()
        self.hide()

def show_about_dialog(parent=None):
    msg = QtWidgets.QMessageBox(parent)
    msg.setWindowTitle("About DesktopPet v3")
    msg.setText("<b>DesktopPet v3</b><br><br>An interactive desktop pet application featuring physics simulation, control panel, and sophisticated system windows behavior.<br><br>Version: 1.0.0<br>Repository: <a href='https://github.com/czarchmA8/DesktopPet_v3' style='color: #0d6efd;'>czarchmA8/DesktopPet_v3</a>")
    msg.setIcon(QtWidgets.QMessageBox.Icon.Information)
    msg.setStyleSheet("QWidget { background-color: #2b2b2b; color: #ffffff; } QPushButton { background-color: #0d6efd; color: white; padding: 5px 15px; }")
    msg.exec()

def run_app(conn, shared_data, log_queue) -> None:
    '''Entry point for the dashboard process'''
    global logger
    logger = setup_process_logger("dashboard", log_queue)
    logger.info("Starting the DASHBOARD process...")

    app = QtWidgets.QApplication(sys.argv)

    window = ControlWindow(conn, shared_data)
    # window.show()

    # Tworzenie tray icon
    tray = QtWidgets.QSystemTrayIcon(QtGui.QIcon("icon.ico"), app)
    menu = QtWidgets.QMenu()
    show_action = menu.addAction("Pokaż Panel")
    show_action.triggered.connect(lambda: (window.show(), window.raise_(), window.activateWindow()))

    about_action = menu.addAction("About/Info")
    about_action.triggered.connect(lambda: show_about_dialog(window))

    menu.addSeparator()
    quit_action = menu.addAction("Wyjdź")
    quit_action.triggered.connect(app.quit)
    tray.setContextMenu(menu)
    tray.show()

    app.aboutToQuit.connect(keyboard.unhook_all)

    sys.exit(app.exec())
