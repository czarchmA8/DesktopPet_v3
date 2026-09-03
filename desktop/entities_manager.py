import sys
import time
import ctypes
from ctypes import wintypes

import win32gui, win32con
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QCoreApplication

import utils_debug
import logger
from windows_z_order.watcher import NeighborsWatcher
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

        self.show()

    def paintEvent(self, event) -> None:
        pass

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

        self.watcher = NeighborsWatcher()
        self.watcher.start()
        self.watch_windows_hwnd: list[int] = []
        self.transparent_windows: dict[int, TransparentWindow] = {}

        self.mods_manager = ModsManager(conn, shared_data)

        # # To jest testowa logika więc usuń to później
        # hwnd = win32gui.FindWindow(None, "Widok główny — Eksplorator plików")
        # self.watch_windows_hwnd.append(hwnd)

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
        if not self.watch_windows_hwnd: # Nie wiem czy ten duplikat nadal jest potrzebny. Przemyśl to później
            hwnd = win32gui.GetForegroundWindow()
            self.watch_windows_hwnd.append(hwnd)

            title = win32gui.GetWindowText(hwnd)
            log.debug(f"Due to empty list, added window {hwnd} ({title}) to watch")

        if self.watcher.changes_detected:
            # Remove windows that have removed or are no longer visible from watchlist
            for hwnd in list(self.watch_windows_hwnd):
                if not win32gui.IsWindow(hwnd) or not win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    log.debug(f"Window {hwnd} ({title}) no longer exists or is hidden — stopped watching it")
                    self.watch_windows_hwnd.remove(hwnd)

            # Adding a window to watch if the list is empty
            if not self.watch_windows_hwnd:
                hwnd = win32gui.GetForegroundWindow()
                self.watch_windows_hwnd.append(hwnd)

                title = win32gui.GetWindowText(hwnd)
                log.debug(f"Due to empty list, added window {hwnd} ({title}) to watch")

            # Getting neighbors of watched windows
            self.watcher.update_neighbor_windows(self.watch_windows_hwnd)
            if self.watcher.old_neighbor_windows != self.watcher.neighbor_windows:
                log.debug("Changes detected in window z-order")

            # Creating and updating z-order `TransparentWindow`
            if self.watcher.neighbor_windows:
                hdwp = self.user32.BeginDeferWindowPos(len(self.watcher.neighbor_windows))
                flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
                for hwnd, neighbors in self.watcher.neighbor_windows.items():
                    if hwnd not in self.transparent_windows:
                        self.transparent_windows[hwnd] = TransparentWindow(hwnd)
                        title = win32gui.GetWindowText(hwnd)
                        log.debug(f'A new layer has been created on the window {hwnd} ({title})')

                    hdwp = self.user32.DeferWindowPos(hdwp, self.transparent_windows[hwnd].hwnd_self, neighbors.window_above, 0, 0, 0, 0, flags)
                self.user32.EndDeferWindowPos(hdwp)

            # Deleting a `TransparentWindow` if the window assigned to it does not exist
            for hwnd in list(self.transparent_windows):
                if hwnd not in self.watcher.neighbor_windows:
                    title = win32gui.GetWindowText(hwnd)
                    log.debug(f'Removed layer assigned to hwnd {hwnd} ({title})')
                    self.transparent_windows[hwnd].close()
                    del self.transparent_windows[hwnd]
        self.process_timer.stop("entities tick")

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
