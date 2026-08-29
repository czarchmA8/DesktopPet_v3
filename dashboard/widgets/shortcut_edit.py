import ctypes
from ctypes import wintypes
from PySide6.QtCore import Qt, QCoreApplication, Signal
from PySide6.QtWidgets import (
    QLineEdit, QDialog, QVBoxLayout,
    QLabel, QHBoxLayout, QPushButton
)
from PySide6.QtGui import QKeySequence, QKeyEvent

class CustomKeySequenceEdit(QLineEdit):
    """Custom QLineEdit for capturing keyboard hotkey sequences"""
    keySequenceChanged = Signal(QKeySequence)

    user32 = ctypes.WinDLL("user32", use_last_error=True)

    user32.MapVirtualKeyExW.restype = wintypes.UINT
    user32.MapVirtualKeyExW.argtypes = (wintypes.UINT, wintypes.UINT, wintypes.HKL)

    user32.GetKeyboardLayout.restype = wintypes.HKL
    user32.GetKeyboardLayout.argtypes = (wintypes.DWORD,)

    user32.GetKeyNameTextW.restype = ctypes.c_int
    user32.GetKeyNameTextW.argtypes = (wintypes.LPARAM, wintypes.LPWSTR, ctypes.c_int)

    def get_key_name(self, vk_code: int | None = None, scan_code: int | None = None) -> str | None:
        """Gets the display name of a key from virtual key code"""
        if vk_code is None and scan_code is None:
            raise Exception("vk_code or scan_code must be provided")

        BUFFER_LEN = 50

        # jeśli scan_code nie podano, vk_code -> scan_code
        if scan_code is None:
            scan_code = self.user32.MapVirtualKeyExW(
                vk_code,
                4,  # 0=MAPVK_VK_TO_VSC, 4=MAPVK_VK_TO_VSC_EX
                self.user32.GetKeyboardLayout(0)
            )

        if not scan_code:
            return None

        # Wyodrębnienie faktu, czy to klawisz rozszerzony oraz samego bazowego kodu skanowania (dolne 8 bitów)
        is_extended = (scan_code & 0xFF00) == 0xE000
        base_scan_code = scan_code & 0xFF

        # Budujemy lParam jak w WM_KEYDOWN
        lparam = (base_scan_code << 16) | 0x1

        # Extended keys - poprawnie ustawiamy bit 24
        if is_extended:
            lparam |= 0x01000000

        # (Opcjonalnie) Ręczne wymuszenie bitu rozszerzonego dla pewności
        # LWIN = 0x5B, RWIN = 0x5C, APPS = 0x5D
        # VK_PRIOR = 0x21
        # VK_HELP = 0x2F
        # if (VK_PRIOR <= vk_code <= VK_HELP) or vk_code in (0x5B, 0x5C, 0x5D):
        #      lparam |= 0x01000000

        # Pobranie nazwy
        buffer = ctypes.create_unicode_buffer(BUFFER_LEN + 1)
        result = self.user32.GetKeyNameTextW(lparam, buffer, BUFFER_LEN)

        if result:
            return buffer.value

        return None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sequence = QKeySequence()
        self.setPlaceholderText(QCoreApplication.translate("KeySequence", "Press key combination...", None))
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

    def keyPressEvent(self, event: QKeyEvent):
        """Handles key press events for hotkey capture"""
        if event.isAutoRepeat():
            return

        if self.clear_keys_pressed:
            self.keys_pressed.clear()
            self.clear_keys_pressed = False

        key_int = event.key()
        modifiers_int = event.modifiers().value
        qt_key = key_int | modifiers_int
        self._sequence = QKeySequence(qt_key)

        self.keySequenceChanged.emit(self._sequence)

        scan_code = event.nativeScanCode()
        virtual_key = event.nativeVirtualKey()

        # Jakaś stara wersja, która nie ogarniała klawiszy Num i strzałek
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

    def keyReleaseEvent(self, event: QKeyEvent):
        """Handles key release events"""
        if event.isAutoRepeat():
            return
        self.clear_keys_pressed = True

class HotkeyDialog(QDialog):
    """Dialog for binding keyboard hotkeys to actions"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("HotkeyDialog", "Record keyboard shortcut", None))
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)

        self.label = QLabel(QCoreApplication.translate("HotkeyDialog", "Press key combination:", None))
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
        layout.addWidget(self.label)

        self.key_sequence_edit = CustomKeySequenceEdit(self)
        layout.addWidget(self.key_sequence_edit)

        self.final_sequence = ""

        # Buttons
        btns = QHBoxLayout()
        self.btn_ok = QPushButton(QCoreApplication.translate("HotkeyDialog", "OK", None))
        self.btn_ok.clicked.connect(self.on_accept)

        btn_cancel = QPushButton(QCoreApplication.translate("HotkeyDialog", "Cancel", None))
        btn_cancel.clicked.connect(self.reject)

        btns.addWidget(self.btn_ok)
        btns.addWidget(btn_cancel)
        layout.addLayout(btns)

    def on_accept(self):
        if len(self.key_sequence_edit.keys_pressed) > 0:
            self.final_sequence = "+".join(self.key_sequence_edit.keys_pressed.keys())
            self.accept()
