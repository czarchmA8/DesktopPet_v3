import sys
import time
import ctypes
from ctypes import wintypes

import win32gui, win32con
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QPainter, QPen

import utils_debug
import logger
from windows_z_order.watcher import WindowsWatcher, WatchWindow
from desktop.mods_manager import ModsManager

log = logger.get_logger("desktop")

class TransparentWindow(QWidget):
    def __init__(self, target_hwnd: int):
        super().__init__()
        self.setWindowTitle("TransparentWindow")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.target_hwnd: int = target_hwnd
        self.hwnd_self = int(self.winId())

        self.draw_commands: list = []

        self.show()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for cmd in self.draw_commands:
            kind = cmd[0]
            if kind == "rect":
                _, x, y, w, h, color, filled = cmd
                painter.setPen(QPen(color))
                painter.setBrush(color if filled else Qt.BrushStyle.NoBrush)
                painter.drawRect(x, y, w, h)
            elif kind == "line":
                _, x1, y1, x2, y2, color, width = cmd
                painter.setPen(QPen(color, width))
                painter.drawLine(x1, y1, x2, y2)
            elif kind == "text":
                _, x, y, text, color, size = cmd
                painter.setPen(QPen(color))
                font = painter.font()
                font.setPointSize(size)
                painter.setFont(font)
                painter.drawText(x, y, text)
            elif kind == "image":
                _, x, y, w, h, pixmap, opacity = cmd
                painter.setOpacity(opacity)
                if w is not None and h is not None:
                    painter.drawPixmap(x, y, w, h, pixmap)
                elif w is not None:
                    h = round(pixmap.height() * (w / pixmap.width()))
                    painter.drawPixmap(x, y, w, h, pixmap)
                elif h is not None:
                    w = round(pixmap.width() * (h / pixmap.height()))
                    painter.drawPixmap(x, y, w, h, pixmap)
                else:
                    painter.drawPixmap(x, y, pixmap)
                painter.setOpacity(1.0)
            else:
                raise Exception(f"Unknown command \"{cmd}\". This shouldn't have happened!")
        painter.end()

    def keyPressEvent(self, event) -> None:
        pass

    def mousePressEvent(self, event) -> None:
        pass

    def mouseMoveEvent(self, event) -> None:
        pass

    def mouseReleaseEvent(self, event) -> None:
        pass

class EntitiesManager(QApplication):
    def __init__(self, conn, shared_data):
        super().__init__(sys.argv)

        self.conn = conn
        self.shared_data = shared_data

        self.watcher = WindowsWatcher()
        self.watcher.start()
        self.transparent_windows: dict[int, TransparentWindow] = {}

        self.mods_manager = ModsManager(conn, shared_data, self)

        # Initialization of the Windows API function to bulk update the z-order of multiple windows in a single operation.
        self.user32 = ctypes.windll.user32
        HDWP = wintypes.HANDLE
        self.user32.BeginDeferWindowPos.argtypes = [ctypes.c_int]
        self.user32.BeginDeferWindowPos.restype = HDWP
        self.user32.DeferWindowPos.argtypes = [HDWP, wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user32.DeferWindowPos.restype = HDWP
        self.user32.EndDeferWindowPos.argtypes = [HDWP]
        self.user32.EndDeferWindowPos.restype = wintypes.BOOL

        # Debugowanie
        self.process_timer = utils_debug.NamedStopwatch(update_rate_sec=1)

        # Timer / dt
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.tick)
        self.refresh_timer.start(1000 // self.shared_data.settings["FPS"])
        self._last_tick_time = time.perf_counter()
        self.dt: float = 0.0

        self.mods_manager.run_mods()

    def tick(self):
        self.process_timer.start("tick")
        # --- Obliczenie Delta Time ---
        now = time.perf_counter()
        self.dt = now - self._last_tick_time
        self._last_tick_time = now
        
        self.process_timer.start("check IPC")
        self._handle_ipc_commands()
        self.process_timer.stop("check IPC")

        self.process_timer.start("entities tick")
        watch_windows: set[WatchWindow] = set()
        for mod in self.mods_manager.mods:
            mod.globals().ModAPI._watch_windows.clear()
            mod.globals().tick()
            watch_windows.update(mod.globals().ModAPI._watch_windows)
        self.process_timer.stop("entities tick")

        self.process_timer.start("update z-order")
        if self.watcher._z_order_changes_detected:
            # Remove windows that have removed or are no longer visible from watchlist
            for window in watch_windows.copy():
                if not win32gui.IsWindow(window.target_hwnd) or not win32gui.IsWindowVisible(window.target_hwnd):
                    title = win32gui.GetWindowText(window.target_hwnd)
                    log.debug(f"Window {window.target_hwnd} ({title}) no longer exists or is hidden — stopped watching it")
                    watch_windows.remove(window)

            # Getting neighbors of watched windows
            self.watcher.update_info_in_watched_windows(watch_windows)
            # if {(w.real_window_above, w.real_window_below) for w in self.watcher.old_watched_windows.values()} != {(w.real_window_above, w.real_window_below) for w in self.watcher.watched_windows.values()}:
            #     log.debug("Changes detected in window z-order")

            # Creating and updating z-order `TransparentWindow`
            if self.watcher.watched_windows:
                hdwp = self.user32.BeginDeferWindowPos(len(self.watcher.watched_windows))
                flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                for hwnd, neighbors in self.watcher.watched_windows.items():
                    if hwnd not in self.transparent_windows:
                        self.transparent_windows[hwnd] = TransparentWindow(hwnd)
                        title = win32gui.GetWindowText(hwnd)
                        log.debug(f'A new layer has been created on the window {hwnd} ({title})')

                    hdwp = self.user32.DeferWindowPos(hdwp, self.transparent_windows[hwnd].hwnd_self, neighbors.window_above, 0, 0, 0, 0, flags)
                self.user32.EndDeferWindowPos(hdwp)

            # Deleting a `TransparentWindow` if the window assigned to it does not exist
            for hwnd in list(self.transparent_windows):
                if hwnd not in self.watcher.watched_windows:
                    title = win32gui.GetWindowText(hwnd)
                    log.debug(f'Removed layer assigned to hwnd {hwnd} ({title})')
                    self.transparent_windows[hwnd].close()
                    del self.transparent_windows[hwnd]
        self.process_timer.stop("update z-order")

        self.process_timer.start("entities paint_tick")
        for window in self.transparent_windows.values():
            window.draw_commands.clear()

        for mod in self.mods_manager.mods:
            mod.globals().paint_tick()

        for window in self.transparent_windows.values():
            window.repaint()
        self.process_timer.stop("entities paint_tick")

        self.process_timer.stop("tick")

    def send_ipc_command(self, msg: list[str]):
        """Sends message to other processes"""
        log.debug(f"Sent IPC: {msg}")
        self.conn.send(msg)

    def _handle_ipc_commands(self):
        """Checks messages from other processes"""
        if self.conn.poll():
            msg = self.conn.recv()
            log.debug(f"Received IPC: {msg}")
            if msg[0] == "close_app":
                self.watcher.stop()
                QCoreApplication.quit()
            else:
                log.error(f"Unknown command: {msg}")

def run_app(conn, shared_data, log_queue):
    logger.init_child(log_queue)
    log.info("Starting the DESKTOP process...")
    app = EntitiesManager(conn, shared_data)
    sys.exit(app.exec())
