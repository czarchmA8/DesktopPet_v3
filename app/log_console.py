import html
import queue
import re
from bisect import bisect_left
from collections import deque
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication, QIcon, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPlainTextEdit, QTextEdit, QToolButton,
    QVBoxLayout, QWidget
)

import app.config as config
from app.ipc import SharedState

Record = tuple[str, str, str]  # (levelname, logger name, message)

LEVEL_COLORS = {
    "DEBUG": "#4fc3c3",
    "INFO": "#5fd35f",
    "WARNING": "#ffd75f",
    "ERROR": "#ff6b6b",
    "CRITICAL": "#ff3b3b",
}
LEVELS = list(LEVEL_COLORS)
DEFAULT_COLOR = "#ddd"
NAME_COLOR = "#b39ddb"
SEPARATOR_COLOR = "#888"
MATCH_BG = "#4d4000"
CURRENT_MATCH_BG = "#9a6a00"
ERROR_COLOR = "#ff6b6b"
MAX_RECORDS = 5000
MAX_LOADED_RECORDS = 20000
MAX_MATCHES = 2000
SEARCH_REFRESH_MS = 150
RERENDER_DELAY_MS = 200
RENDER_CHUNK = 1000

# A line written by logger.py:  [time]-[LEVEL]-(file.py:123) -> message
_LOG_LINE = re.compile(r"\[.*?\]-\[(?P<level>[A-Z]+)\]-\((?P<source>.*?)\) -> ?(?P<message>.*)")
_ASTRAL = re.compile("[\U00010000-\U0010FFFF]")

STYLE = """
#LogWindow { background:#1e1e1e; }
QPlainTextEdit { background:#1e1e1e; color:#ddd; font-family:Consolas,monospace; border:none; }
QCheckBox { color:#ddd; font-family:Consolas,monospace; }
QLineEdit { background:#2b2b2b; color:#ddd; border:1px solid #444; padding:2px 4px; font-family:Consolas,monospace; }
QToolButton { background:transparent; color:#ddd; border:1px solid transparent; border-radius:3px; padding:1px 6px; font-family:Consolas,monospace; }
QToolButton:hover { background:#333; }
QToolButton:checked { background:#094771; border:1px solid #1177bb; }
QLabel { color:#aaa; font-family:Consolas,monospace; }
"""

def parse_log_file(path: Path) -> tuple[list[Record], int]:
    """Reads a .log file written by logger.py.

    Lines that don't start a record (tracebacks, multi-line messages) are added to the previous record.
    Returns (the last MAX_LOADED_RECORDS records, total number of records)."""
    records: deque[list[str]] = deque(maxlen=MAX_LOADED_RECORDS)
    total = 0
    with path.open(encoding="utf-8", errors="replace") as file:
        for line in file:
            line = line.rstrip("\r\n")
            match = _LOG_LINE.match(line)
            if match:
                records.append([match["level"], match["source"], match["message"]])
                total += 1
            elif total:
                records[-1][2] += "\n" + line
            else:
                records.append(["", "", line])
                total += 1
    return [(level, name, message) for level, name, message in records], total

class SearchLineEdit(QLineEdit):
    """Search field: Enter -> next occurrence, Shift+Enter -> previous occurrence."""
    next_requested = Signal()
    previous_requested = Signal()

    def keyPressEvent(self, event) -> None:
        """Emits next/previous_requested on Enter/Shift+Enter, otherwise handles the key normally."""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.previous_requested.emit()
            else:
                self.next_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

class LogWindow(QWidget):
    """Log console. Shows either the current session or a loaded old log file (never both), with level filters and search."""
    visibility_changed = Signal(bool)

    def __init__(self, gui_queue, shared_data: SharedState) -> None:
        """Builds the window, the search bar, the timers and the signal connections."""
        super().__init__()
        self.setObjectName("LogWindow")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setWindowTitle("Logs")
        self.setWindowIcon(QIcon(str(config.RESOURCE_DIR / "icon.ico")))
        self.setStyleSheet(STYLE)
        self.resize(900, 500)

        self.gui_queue = gui_queue
        self.shared_data: SharedState = shared_data

        self._records: deque[Record] = deque(maxlen=MAX_RECORDS)
        self._loaded: list[Record] = []
        self._loaded_name = ""
        self._showing_loaded = False
        self._hidden_levels: set[str] = set()
        self._was_shown = False

        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(MAX_RECORDS)
        self.view.setUndoRedoEnabled(False)

        self._checkboxes: dict[str, QCheckBox] = {}
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(8, 4, 8, 0)
        for level, color in LEVEL_COLORS.items():
            checkbox = QCheckBox(level)
            checkbox.setStyleSheet(f"color:{color};")
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda checked, lvl=level: self._on_filter_toggled(lvl, checked))
            self._checkboxes[level] = checkbox
            filter_row.addWidget(checkbox)
        filter_row.addStretch(1)
        self.wrap_checkbox = QCheckBox("Wrap lines")
        self.wrap_checkbox.setChecked(True)
        self.wrap_checkbox.toggled.connect(self._on_wrap_toggled)
        filter_row.addWidget(self.wrap_checkbox)
        self.btn_load = self._make_button("Load log\u2026", "Load an old log file (*.log)")
        self.btn_load.clicked.connect(lambda: self.load_log_file())
        filter_row.addWidget(self.btn_load)
        self.btn_switch = self._make_button(
            "Show old log", "Switch between the loaded old log and the current session (Alt+L)", "Alt+L"
        )
        self.btn_switch.clicked.connect(self._toggle_loaded_view)
        self.btn_switch.setVisible(False)
        filter_row.addWidget(self.btn_switch)

        self._matches: list[tuple[int, int]] = []
        self._matches_capped = False
        self._current = -1
        self._search_error: str | None = None

        self.search_edit = SearchLineEdit()
        self.search_edit.setPlaceholderText("Search (Ctrl+F)")
        self.search_edit.setClearButtonEnabled(True)
        self.btn_case = self._make_button("Aa", "Match Case (Alt+C)", "Alt+C", checkable=True)
        self.btn_words = self._make_button("W", "Words (Alt+W)", "Alt+W", checkable=True)
        self.btn_regex = self._make_button(".*", "Regex (Alt+R)", "Alt+R", checkable=True)
        self.btn_filter = self._make_button("Filter", "Show only logs containing the search text", checkable=True)
        self.match_label = QLabel()
        self.match_label.setMinimumWidth(80)
        self.btn_prev = self._make_button("\u25b2", "Previous occurrence (Shift+Enter, Shift+F3)")
        self.btn_next = self._make_button("\u25bc", "Next occurrence (Enter, F3)")

        search_row = QHBoxLayout()
        search_row.setContentsMargins(8, 0, 8, 0)
        search_row.setSpacing(4)
        search_row.addWidget(self.search_edit, 1)
        for widget in (self.btn_case, self.btn_words, self.btn_regex, self.btn_filter, self.match_label, self.btn_prev, self.btn_next):
            search_row.addWidget(widget)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addLayout(filter_row)
        layout.addLayout(search_row)
        layout.addWidget(self.view)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(SEARCH_REFRESH_MS)
        self._search_timer.timeout.connect(self._refresh_search)

        self._rerender_timer = QTimer(self)
        self._rerender_timer.setSingleShot(True)
        self._rerender_timer.setInterval(RERENDER_DELAY_MS)
        self._rerender_timer.timeout.connect(self._rerender_and_search)

        self.search_edit.textChanged.connect(lambda: self._on_search_input_changed())
        for button in (self.btn_case, self.btn_words, self.btn_regex):
            button.toggled.connect(lambda: self._on_search_input_changed())
        self.btn_filter.toggled.connect(lambda: self._rerender_and_search())
        self.btn_next.clicked.connect(lambda: self._goto_match(1))
        self.btn_prev.clicked.connect(lambda: self._goto_match(-1))
        self.search_edit.next_requested.connect(lambda: self._goto_match(1))
        self.search_edit.previous_requested.connect(lambda: self._goto_match(-1))
        QShortcut(QKeySequence("F3"), self).activated.connect(lambda: self._goto_match(1))
        QShortcut(QKeySequence("Shift+F3"), self).activated.connect(lambda: self._goto_match(-1))
        QShortcut(QKeySequence("Ctrl+F"), self).activated.connect(self._focus_search)
        self.view.document().contentsChanged.connect(self._schedule_search_refresh)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll)
        self.timer.start(100)

        self.restore_state()
        self.setVisible(shared_data.settings["debug"]["active"] and shared_data.settings["debug"]["console"]["show_console_on_startup"])
        self._restore_geometry()

    # --- State ---
    def restore_state(self) -> None:
        """Loads the hidden levels from settings, updates the checkboxes and re-renders the view."""
        console_settings = self.shared_data.settings["debug"]["console"]
        self._hidden_levels = {lvl for lvl in console_settings["hidden_levels"] if lvl in LEVEL_COLORS}
        for level, checkbox in self._checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(level not in self._hidden_levels)
            checkbox.blockSignals(False)
        self._render_all()

    def _restore_geometry(self) -> None:
        """Restores the saved window size and position, falling back to the screen center if it would be off-screen."""
        geometry_settings = self.shared_data.settings["debug"]["console"]["window_geometry"]
        if not geometry_settings["restore"]:
            return
        x, y, width, height = (geometry_settings.get(key) for key in ("x", "y", "width", "height"))
        if None in (x, y, width, height):
            return

        saved_screen_name = geometry_settings.get("screen_name")
        screen = next((s for s in QGuiApplication.screens() if s.name() == saved_screen_name), None)
        found_screen = screen is not None
        screen = screen or QGuiApplication.primaryScreen()
        available = screen.availableGeometry()

        width, height = min(width, available.width()), min(height, available.height())
        self.resize(width, height)

        title_bar = QRect(x, y, width, 40).intersected(available)
        if found_screen and title_bar.width() >= 100 and title_bar.height() >= 20:
            self.move(x, y)
        else:
            frame = self.frameGeometry()
            frame.moveCenter(available.center())
            self.move(frame.topLeft())

    def save_state_to_settings(self) -> None:
        """Writes the hidden levels and window geometry into the settings dict (call before saving settings.json)."""
        console_settings = self.shared_data.settings["debug"]["console"]
        console_settings["hidden_levels"] = [lvl for lvl in LEVELS if lvl in self._hidden_levels]

        if not self._was_shown or self.isMinimized() or self.isMaximized():
            return
        screen = self.screen() or QGuiApplication.primaryScreen()
        console_settings["window_geometry"].update({
            "x": self.pos().x(),
            "y": self.pos().y(),
            "width": self.width(),
            "height": self.height(),
            "screen_name": screen.name(),
        })

    # --- Rendering and filter ---
    @staticmethod
    def _format(levelname: str, name: str, message: str) -> str:
        """Returns a record as colored HTML. A record without a level (separator, stray line) is gray."""
        if not levelname:
            return f'<span style="color:{SEPARATOR_COLOR}; white-space:pre-wrap">{html.escape(message)}</span>'
        color = LEVEL_COLORS.get(levelname, DEFAULT_COLOR)
        return (
            f'<span style="color:{color}; white-space:pre-wrap">[{levelname}] '
            f'<span style="color:{NAME_COLOR}">{html.escape(name)}</span>: '
            f'{html.escape(message)}</span>'
        )

    def _on_filter_toggled(self, level: str, checked: bool) -> None:
        """Shows or hides a log level and re-renders the view."""
        if checked:
            self._hidden_levels.discard(level)
        else:
            self._hidden_levels.add(level)
        self._render_all()

    @staticmethod
    def _entry_text(entry: Record) -> str:
        """Returns the plain text of a record, as it appears in the view."""
        levelname, name, message = entry
        return f"[{levelname}] {name}: {message}" if levelname else message

    def _is_visible(self, entry: Record, pattern: re.Pattern | None) -> bool:
        """Returns True if the record's level is not hidden and it matches the filter pattern (if any)."""
        if entry[0] in self._hidden_levels:
            return False
        return pattern is None or pattern.search(self._entry_text(entry)) is not None

    def _render_all(self) -> None:
        """Re-renders the view from the loaded old log or the current session, applying the level and search filters."""
        pattern = self._filter_pattern()
        chunks: list[str] = []
        parts: list[str] = []
        for entry in self._loaded if self._showing_loaded else self._records:
            if not self._is_visible(entry, pattern):
                continue
            parts.append(f"<div>{self._format(*entry)}</div>")
            if len(parts) == RENDER_CHUNK:
                chunks.append("".join(parts))
                parts = []
        if parts:
            chunks.append("".join(parts))

        self.view.setUpdatesEnabled(False)
        self.view.setMaximumBlockCount(0 if self._showing_loaded else MAX_RECORDS)
        self.view.clear()
        cursor = QTextCursor(self.view.document())
        for index, chunk in enumerate(chunks):
            if index:
                cursor.insertBlock()
            cursor.insertHtml(chunk)
        self.view.setUpdatesEnabled(True)

        scrollbar = self.view.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _update_view_mode(self) -> None:
        """Updates the switch button and the window title to match what the view shows."""
        self.btn_switch.setVisible(bool(self._loaded))
        self.btn_switch.setText("Show current session" if self._showing_loaded else "Show old log")
        self.setWindowTitle(f"Logs \u2014 old log: {self._loaded_name}" if self._showing_loaded else "Logs")

    def _toggle_loaded_view(self) -> None:
        """Switches the view between the loaded old log and the current session."""
        if not self._loaded:
            return
        self._showing_loaded = not self._showing_loaded
        self._update_view_mode()
        self._rerender_and_search()

    def _on_wrap_toggled(self, checked: bool) -> None:
        """Turns line wrapping on or off."""
        self.view.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth if checked else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def load_log_file(self, path: str | Path | None = None) -> None:
        """Loads an old log file and shows it instead of the current session. Without a path, asks for one in a dialog."""
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self, "Load old log", str(config.APP_DIR / "logs"), "Log files (*.log);;All files (*)"
            )
            if not path:
                return
        path = Path(path)
        try:
            records, total = parse_log_file(path)
        except OSError as e:
            QMessageBox.warning(self, "Load old log", f'Failed to read "{path.name}":\n{e}')
            return

        count = f"last {len(records)} of {total} records" if len(records) < total else f"{total} records"
        begin_marker = ("", "", f"\u2500\u2500\u2500 Old log: {path.name} ({count}) \u2500\u2500\u2500")
        end_marker = ("", "", "\u2500\u2500\u2500 End of old log \u2500\u2500\u2500")
        self._loaded = [begin_marker, *records, end_marker]
        self._loaded_name = path.name
        self._showing_loaded = True
        self._update_view_mode()
        self._rerender_and_search()

    # --- Search ---
    @staticmethod
    def _make_button(text: str, tooltip: str, shortcut: str | None = None, checkable: bool = False) -> QToolButton:
        """Returns a flat toolbar button with an optional shortcut."""
        button = QToolButton()
        button.setText(text)
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        if shortcut:
            button.setShortcut(QKeySequence(shortcut))
        return button

    def _focus_search(self) -> None:
        """Focuses the search field and selects its text."""
        self.search_edit.setFocus()
        self.search_edit.selectAll()

    def _build_search_pattern(self) -> tuple[re.Pattern | None, str | None]:
        """Compiles the search query using the Aa / W / .* buttons. Returns (pattern, error); each is None if not applicable."""
        query = self.search_edit.text()
        if not query:
            return None, None
        pattern = query if self.btn_regex.isChecked() else re.escape(query)
        if self.btn_words.isChecked():
            pattern = rf"(?<!\w)(?:{pattern})(?!\w)"
        flags = re.MULTILINE | (0 if self.btn_case.isChecked() else re.IGNORECASE)
        try:
            return re.compile(pattern, flags), None
        except re.error as e:
            return None, str(e)

    def _compile_search(self) -> re.Pattern | None:
        """Like _build_search_pattern, but also shows the error on the search field. Returns the pattern or None."""
        pattern, self._search_error = self._build_search_pattern()
        if self._search_error:
            self.search_edit.setStyleSheet(f"QLineEdit {{ border:1px solid {ERROR_COLOR}; }}")
            self.search_edit.setToolTip(f"Invalid regex: {self._search_error}")
        else:
            self.search_edit.setStyleSheet("")
            self.search_edit.setToolTip("")
        return pattern

    def _filter_pattern(self) -> re.Pattern | None:
        """Returns the pattern for the "Filter" button, or None if the filter is off or the query is empty/invalid."""
        return self._build_search_pattern()[0] if self.btn_filter.isChecked() else None

    def _on_search_input_changed(self) -> None:
        """Reacts to a change of the query or search options: re-renders (Filter on, debounced) or re-highlights."""
        if self.btn_filter.isChecked():
            self._rerender_timer.start()
        else:
            self._refresh_search(reset=True)

    def _rerender_and_search(self) -> None:
        """Re-renders the view and searches it again from the top."""
        self._rerender_timer.stop()
        self._render_all()
        self._refresh_search(reset=True)

    def _schedule_search_refresh(self) -> None:
        """Starts a debounced search refresh after the view content changed."""
        if self.search_edit.text() and not self._search_timer.isActive():
            self._search_timer.start()

    def _refresh_search(self, reset: bool = False) -> None:
        """Finds all matches in the view and highlights them. With reset=True jumps to the first match below the top of the view."""
        pattern = self._compile_search()
        self._matches = []
        self._matches_capped = False
        if pattern is not None:
            text = self.view.toPlainText()
            astral = [m.start() for m in _ASTRAL.finditer(text)]
            for match in pattern.finditer(text):
                start, end = match.span()
                if start == end:
                    continue
                if len(self._matches) >= MAX_MATCHES:
                    self._matches_capped = True
                    break
                self._matches.append((start + bisect_left(astral, start), end + bisect_left(astral, end)))

        if not self._matches:
            self._current = -1
        elif reset or self._current < 0:
            top = self.view.cursorForPosition(QPoint(0, 0)).position()
            index = bisect_left([start for start, _ in self._matches], top)
            self._current = index if index < len(self._matches) else len(self._matches) - 1
        else:
            self._current = min(self._current, len(self._matches) - 1)

        self._apply_highlights()
        self._update_match_label()
        if reset and self._current >= 0:
            self._scroll_to_current()

    def _goto_match(self, step: int) -> None:
        """Moves to the next (step=1) or previous (step=-1) match, wrapping around."""
        if not self._matches:
            return
        self._current = (self._current + step) % len(self._matches)
        self._apply_highlights()
        self._update_match_label()
        self._scroll_to_current()

    def _scroll_to_current(self) -> None:
        """Scrolls the view to the current match."""
        cursor = QTextCursor(self.view.document())
        cursor.setPosition(min(self._matches[self._current][0], self.view.document().characterCount() - 1))
        self.view.setTextCursor(cursor)
        self.view.ensureCursorVisible()

    def _apply_highlights(self) -> None:
        """Highlights all matches, the current one more strongly."""
        document = self.view.document()
        limit = document.characterCount() - 1
        selections = []
        for index, (start, end) in enumerate(self._matches):
            if end > limit:
                continue
            cursor = QTextCursor(document)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            if index == self._current:
                selection.format.setBackground(QColor(CURRENT_MATCH_BG))
                selection.format.setForeground(QColor("#ffffff"))
            else:
                selection.format.setBackground(QColor(MATCH_BG))
            selections.append(selection)
        self.view.setExtraSelections(selections)

    def _update_match_label(self) -> None:
        """Shows "current/total", "No results" or "Invalid regex" next to the search field."""
        color = "#aaa"
        if self._search_error:
            text, color = "Invalid regex", ERROR_COLOR
        elif not self.search_edit.text():
            text = ""
        elif not self._matches:
            text, color = "No results", ERROR_COLOR
        else:
            text = f"{self._current + 1}/{len(self._matches)}{'+' if self._matches_capped else ''}"
        self.match_label.setText(text)
        self.match_label.setStyleSheet(f"color:{color};")

    # --- Window events ---
    def showEvent(self, event) -> None:
        """Remembers that the window was shown and emits visibility_changed(True)."""
        super().showEvent(event)
        self._was_shown = True
        self.visibility_changed.emit(True)

    def hideEvent(self, event) -> None:
        """Emits visibility_changed(False), unless the window was only minimized by the system."""
        super().hideEvent(event)
        if not event.spontaneous():
            self.visibility_changed.emit(False)

    def closeEvent(self, event) -> None:
        """Hides the window instead of closing it."""
        event.ignore()
        self.hide()

    # --- Log polling ---
    def poll(self) -> None:
        """Takes up to 200 new records from the queue per call and shows them. Shows the window on an error if enabled in settings."""
        error = False
        pattern = self._filter_pattern()
        for _ in range(200):
            try:
                record = self.gui_queue.get_nowait()
            except queue.Empty:
                break
            if record.levelno >= 40:
                error = True
            entry = (record.levelname, record.name, record.getMessage())
            self._records.append(entry)
            if not self._showing_loaded and self._is_visible(entry, pattern):
                self.view.appendHtml(self._format(*entry))

        if error:
            self.shared_data.pull()
            debug = self.shared_data.settings["debug"]
            if debug["active"] and debug["console"]["show_console_on_error"]:
                self.show()
