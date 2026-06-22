from PyQt6 import QtWidgets, QtCore, QtGui
import re
from dataclasses import is_dataclass, dataclass, fields, field
from typing import Optional
import time

def format_number(number: int | float | str, separator: str = " ") -> str:
    """Formats a number by adding thousand separators"""
    if isinstance(number, str):
        number = number.strip()
        number = float(number) if "." in number else int(number)
    if isinstance(number, float):
        formatted = f"{number:,}".rstrip("0").rstrip(".")
    else:
        formatted = f"{number:,}"
    return formatted.replace(",", separator)

class Color:
    """Color as an anchored marker for text coloring. Use: f'{Color.White}text{Color.Red}some text'"""

    # Predefiniowane kolory
    WHITE = "\x00WHITE\x00"
    BLACK = "\x00BLACK\x00"
    RED = "\x00RED\x00"
    GREEN = "\x00GREEN\x00"
    BLUE = "\x00BLUE\x00"
    YELLOW = "\x00YELLOW\x00"
    CYAN = "\x00CYAN\x00"
    MAGENTA = "\x00MAGENTA\x00"
    GRAY = "\x00GRAY\x00"
    LIGHT_GRAY = "\x00LIGHT_GRAY\x00"

    _NAMED_COLORS = {
        'WHITE': (255, 255, 255),
        'BLACK': (0, 0, 0),
        'RED': (255, 0, 0),
        'GREEN': (0, 255, 0),
        'BLUE': (0, 0, 255),
        'YELLOW': (255, 255, 0),
        'CYAN': (0, 255, 255),
        'MAGENTA': (255, 0, 255),
        'GRAY': (128, 128, 128),
        'LIGHT_GRAY': (211, 211, 211),
    }

    def __init__(self, r: int, g: int, b: int):
        """Creates a color from RGB. Usage: Color(255, 0, 0)"""
        self.r = r
        self.g = g
        self.b = b
        self.marker = f"\x00RGB:{self.r},{self.g},{self.b}\x00"

    def __str__(self):
        return self.marker

    class StringifyColors:
        '''Color configuration for different value types'''
        def __init__(self,
                     color_str: 'Color'=None,
                     color_int: 'Color'=None,
                     color_float: 'Color'=None,
                     color_false: 'Color'=None,
                     color_true: 'Color'=None,
                     color_none: 'Color'=None,
                     color_list: 'Color'=None,
                     color_dict: 'Color'=None,
                     color_tuple: 'Color'=None,
                     color_class: 'Color'=None,
                     color_arg: 'Color'=None
                     ):
            self.color_str = color_str if color_str else Color(0, 200, 0)
            self.color_int = color_int if color_int else Color(0, 200, 0)
            self.color_float = color_float if color_float else Color(0, 200, 0)
            self.color_false = color_false if color_false else Color(200, 100, 0)
            self.color_true = color_true if color_true else Color(200, 200, 0)
            self.color_none = color_none if color_none else Color(0, 200, 0)
            self.color_list = color_list if color_list else Color(200, 220, 200)
            self.color_dict = color_dict if color_dict else Color(200, 220, 200)
            self.color_tuple = color_tuple if color_tuple else Color(200, 220, 200)
            self.color_class = color_class if color_class else Color(200, 220, 200)
            self.color_arg = color_arg if color_arg else self.color_class

        def stringify(self, obj) -> str:
            return self._stringify_recursive(obj)

        def _stringify_recursive(self, val, depth=0):
            """Recursively converts values to colored strings with nesting support"""
            # None
            if val is None:
                return f"{self.color_none}None"

            # Bool (musi być przed int, bo bool to podklasa int)
            if isinstance(val, bool):
                color = self.color_true if val else self.color_false
                return f"{color}{str(val)}"

            # Int
            if isinstance(val, int):
                return f"{self.color_int}{str(val)}"

            # Float
            if isinstance(val, float):
                return f"{self.color_float}{str(val)}"

            # String
            if isinstance(val, str):
                return f"{self.color_str}'{val}'"

            # List
            if isinstance(val, list):
                if not val:
                    return f"{self.color_list}[]"
                items = ", ".join(self._stringify_recursive(item, depth + 1) for item in val)
                return f"{self.color_list}[{items}{self.color_list}]"

            # Tuple
            if isinstance(val, tuple):
                if not val:
                    return f"{self.color_tuple}()"
                items = ", ".join(self._stringify_recursive(item, depth + 1) for item in val)
                return f"{self.color_tuple}({items}{self.color_tuple})"

            # Dict
            if isinstance(val, dict):
                if not val:
                    return f"{self.color_dict}{{}}"
                items = ", ".join(
                    f"{self._stringify_recursive(k, depth + 1)}: {self._stringify_recursive(v, depth + 1)}"
                    for k, v in val.items()
                )
                return f"{self.color_dict}{{{items}{self.color_dict}}}"

            # Dataclass
            if is_dataclass(val) and not isinstance(val, type):
                class_name = val.__class__.__name__
                field_strs = []
                for field in fields(val):
                    field_name = field.name
                    field_value = self._stringify_recursive(getattr(val, field.name), depth + 1)
                    field_strs.append(f"{self.color_arg}{field_name}{self.color_class}={field_value}")
                items = ", ".join(field_strs)
                return f"{self.color_class}{class_name}({items}{self.color_class})"

            # Custom class
            return f"{self.color_class}{str(val)}"

class HitboxOverlay(QtWidgets.QWidget):
    '''Widget for displaying hitbox overlays'''
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Hitbox overlay")
        self.setWindowFlags(
            QtCore.Qt.WindowType.FramelessWindowHint |
            QtCore.Qt.WindowType.WindowStaysOnTopHint |
            QtCore.Qt.WindowType.Tool
        )
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

        # Dane do rysowania
        self.rects: list[tuple[int, int, int, int]] = []
        self.masks: list[tuple] = []  # Lista krotek: (QImage, x, y)

        # Pobranie wirtualnej geometrii (wszystkie monitory)
        app = QtWidgets.QApplication.instance()
        virtual_geometry = app.primaryScreen().virtualGeometry()

        # Śledzenie offsetu ekranu głównego w systemie wirtualnym
        screens = app.screens()
        min_x = min(screen.geometry().x() for screen in screens)
        min_y = min(screen.geometry().y() for screen in screens)

        primary_geometry = app.primaryScreen().geometry()
        self.primary_offset_x = primary_geometry.x() - min_x
        self.primary_offset_y = primary_geometry.y() - min_y

        self.setGeometry(virtual_geometry)
        self.show()

    def update_hitboxes(self, rects: list = None, masks: list = None):
        """
        Updates hitbox overlay with rectangles and masks

        rects: lista krotek ((x,y,w,h), kolor)
        masks: lista krotek (QImage, x, y)
        """
        self.rects = [] if rects is None else rects
        self.masks = [] if masks is None else masks
        self.update()

    def paintEvent(self, event):
        '''Paints hitboxes and masks on the overlay'''
        painter = QtGui.QPainter(self)
        # painter.setRenderHint(QtGui.QPainter.Antialiasing)

        # 1. Rysowanie Masek (obrazków hitboxów)
        if self.masks:
            painter.setOpacity(0.5)
            for img, x, y in self.masks:
                if img and not img.isNull():
                    # Konwersja z lokalnych współrzędnych ekranu głównego na wirtualne
                    draw_x = x + self.primary_offset_x
                    draw_y = y + self.primary_offset_y
                    painter.drawImage(draw_x, draw_y, img)
            painter.setOpacity(1.0)

        # 2. Rysowanie Prostokątów (bounding boxów)
        if self.rects:
            for rect, color in self.rects:
                pen = QtGui.QPen(QtGui.QColor(*color), 2)
                painter.setPen(pen)
                # Obsługa rect: (x1, y1, x2, y2)
                # Konwersja z lokalnych współrzędnych ekranu głównego na wirtualne
                x1 = int(rect[0]) + self.primary_offset_x
                y1 = int(rect[1]) + self.primary_offset_y
                x2 = int(rect[2]) + self.primary_offset_x
                y2 = int(rect[3]) + self.primary_offset_y
                painter.drawRect(x1, y1, x2 - x1, y2 - y1)

class DebugWindow(QtWidgets.QWidget):
    """
    Debug information display window

    Use:
        debug = DebugWindow()
        debug.update_debug(f"{Color.White}pos: {Color(255, 255, 0)}({x}, {y})")
        debug.update_debug(f"{Color.Red}ERROR: {Color.White}Something went wrong")
    """

    def __init__(self, monitor_index: int = 1, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pet Debug")
        self.setWindowFlags(QtCore.Qt.WindowType.WindowStaysOnTopHint | QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Layout
        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)

        # Przycisk zamknięcia
        btn_close = QtWidgets.QPushButton("Zamknij panel")
        btn_close.clicked.connect(self.hide)
        btn_close.setMaximumHeight(25)
        self.layout.addWidget(btn_close)

        # Text edit do wyświetlania tekstu
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setFont(QtGui.QFont("Consolas", 20))
        self.text_edit.setStyleSheet("border: 1px solid #ccc;")
        self.layout.addWidget(self.text_edit)

        self.setLayout(self.layout)
        self.setGeometry(0, 0, 1150, 800)

        # Pozycjonowanie na żądanym monitorze
        screens = QtWidgets.QApplication.instance().screens()
        if monitor_index < len(screens):
            target = screens[monitor_index].availableGeometry()
        else:
            target = screens[0].availableGeometry()
        self.move(target.x() + 20, target.y() + 20)
        self.show()

    @staticmethod
    def _parse_colored_text(text: str) -> str:
        """
        Parses text with color markers and converts to HTML

        Tag formats:
            \x00WHITE\x00
            \x00RGB:255,0,0\x00
        """
        html = ""
        pos = 0
        current_color = None

        # Znajdź wszystkie znaczniki kolorów
        pattern = r'\x00(WHITE|BLACK|RED|GREEN|BLUE|YELLOW|CYAN|MAGENTA|GRAY|LIGHT_GRAY|RGB:\d+,\d+,\d+)\x00'

        for match in re.finditer(pattern, text):
            # Dodaj tekst przed znacznikiem
            if pos < match.start():
                chunk = text[pos:match.start()]
                if current_color:
                    html += f'<span style="color: {current_color};">{chunk}</span>'
                else:
                    html += chunk

            # Parsuj kolor z znacznika
            color_spec = match.group(1)
            if color_spec.startswith('RGB:'):
                r, g, b = map(int, color_spec[4:].split(','))
                current_color = f"#{r:02x}{g:02x}{b:02x}"
            else:
                rgb = Color._NAMED_COLORS.get(color_spec, (255, 255, 255))
                current_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

            pos = match.end()

        # Dodaj pozostały tekst
        if pos < len(text):
            chunk = text[pos:]
            if current_color:
                html += f'<span style="color: {current_color};">{chunk}</span>'
            else:
                html += chunk

        return html if html else text

    def update_debug(self, text: str):
        """
        Updates debug window content with color markers

        Example:
            debug.update_debug(f"{Color.White}pos: {Color(255, 255, 0)}({x}, {y})")
            debug.update_debug(f"{Color.Red}Line 1\n{Color.Green}Line 2")
        """
        html_text = self._parse_colored_text(text)
        # Zamień znaki nowej linii na <br>
        html_text = html_text.replace('\n', '<br>')
        self.text_edit.setHtml(html_text)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

def show_details(variable, logger) -> None:
    '''Debug function that displays the contents of a variable'''
    from logging import DEBUG as logging_DEBUG
    if not logger.isEnabledFor(logging_DEBUG):
        return
    logger.debug(f"--- Details of object type: {type(variable).__name__} ---")
    details = {z: getattr(variable, z) for z in dir(variable) if not z.startswith('__')}
    for key, value in details.items():
        logger.debug(f"\033[31m{key}\033[39m: \033[32m{value}  \033[39m(\033[33m{type(value)}\033[39m)")
    # input("Kliknij Enter: ")

class NamedStopwatch:
    '''Named timer for performance measurement'''
    class _Timer:
        '''Individual timer container'''
        @dataclass
        class _Time:
            '''Time sample dataclass'''
            start: float
            end: Optional[float] = None

        def __init__(self):
            self.samples: list["NamedStopwatch._Timer._Time"] = []
            self.sum_samples: float = 0.0
            self.average_time: float = 0.0
            self._last_update_time: float = time.perf_counter()

    def __init__(self, /, samples_per_update: int = None, update_rate_sec: float = None):
        self.samples_per_update = samples_per_update
        self.update_rate_sec = update_rate_sec
        self.timers: dict[str, NamedStopwatch._Timer] = {}

        if self.samples_per_update is not None and self.update_rate_sec is not None:
            raise ValueError("You can provide either 'samples_per_update' or 'update_rate_sec', but not both.")
        elif self.samples_per_update is None and self.update_rate_sec is None:
            self.samples_per_update = 10

    def start(self, name: str) -> None:
        timer = self.timers.setdefault(name, self._Timer())
        if timer.samples and timer.samples[-1].end is None:
            raise ValueError("You must stop the stopwatch before starting it again")
        timer.samples.append(self._Timer._Time(time.perf_counter()))

    def stop(self, name: str) -> None:
        if name not in self.timers:
            raise ValueError(f'Stoper o nazwie "{name}" nie istnieje')

        timer = self.timers[name]
        if not timer.samples:
            raise ValueError("You must start the stopwatch before stopping it")
        if timer.samples[-1].end is not None:
            raise ValueError("Cannot stop the stopwatch more than once")

        now = time.perf_counter()
        last = timer.samples[-1]
        last.end = now

        elapsed = now - last.start
        timer.sum_samples += elapsed

        self._update_average_time(name)

    def add_time(self, name: str, result_time: float | int, is_start_time: bool=False) -> None:
        now = time.perf_counter()

        timer = self.timers.setdefault(name, self._Timer())
        timer.samples.append(self._Timer._Time(now - result_time, now))
        timer.sum_samples += result_time

        self._update_average_time(name)

    def _update_average_time(self, name: str, /, ignore_error: bool=False) -> None:
        if name not in self.timers:
            if ignore_error:
                return
            else:
                raise ValueError(f'Stoper o nazwie "{name}" nie istnieje')

        now = time.perf_counter()
        timer = self.timers[name]
        if ((self.samples_per_update and len(timer.samples) >= self.samples_per_update) or
            (self.update_rate_sec and ((now - timer._last_update_time if len(timer.samples) == 0 else now - timer.samples[0].start) > self.update_rate_sec))
        ):
            if len(timer.samples) == 0:
                timer.average_time = 0.0
            else:
                timer.average_time = timer.sum_samples / len(timer.samples)
            timer.samples.clear()
            timer.sum_samples = 0.0
            timer._last_update_time = now

    def get_avg_time(self, name: str) -> float:
        if name not in self.timers:
            raise ValueError(f'Stoper o nazwie "{name}" nie istnieje')
        return self.timers[name].average_time

    def get_avg_fps(self, name: str) -> int:
        if name not in self.timers:
            raise ValueError(f'Stoper o nazwie "{name}" nie istnieje')
        return round(1 / self.timers[name].average_time) if self.timers[name].average_time != 0 else 0

    def get_timers(self) -> list:
        return [name for name in self.timers.keys()]

    def remove_timer(self, name: str) -> None:
        if name not in self.timers:
            raise ValueError(f'Stoper o nazwie "{name}" nie istnieje')
        del self.timers[name]

    def remove_timers(self) -> None:
        self.timers.clear()
