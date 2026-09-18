import sys
import time
import ctypes
from ctypes import wintypes

import win32gui, win32con, win32api
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QCoreApplication
from PySide6.QtGui import QPainter, QPen, QWheelEvent, QMouseEvent, QPaintEvent

import utils_debug
import logger
from shared_state import SharedState
from windows_z_order.watcher import WindowsWatcher, WindowNeighbors
from desktop.mods_manager import ModsManager
from desktop.input_events import InputState, MouseButtonEvent

log = logger.get_logger("overlay_manager")

class TransparentWindow(QWidget):
    def __init__(self, target_hwnd: int, mods_manager: ModsManager):
        super().__init__()
        self.mods_manager: ModsManager = mods_manager
        
        self.setWindowTitle("TransparentWindow")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        vx = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        vy = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        vw = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        vh = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        self.setGeometry(vx, vy, vw, vh)

        self.target_hwnd: int = target_hwnd
        self.hwnd_self = int(self.winId())

        self.draw_commands: list = []

        self.show()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for cmd in self.draw_commands:
            kind = cmd[0]
            if kind == "rect":
                _, x, y, w, h, color, filled, hit_id = cmd
                painter.setPen(QPen(color))
                painter.setBrush(color if filled else Qt.BrushStyle.NoBrush)
                painter.drawRect(x, y, w, h)
            elif kind == "line":
                _, x1, y1, x2, y2, color, width, hit_id = cmd
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
                _, x, y, w, h, pixmap, opacity, _alpha_image, hit_id = cmd
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

    def mousePressEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        button_name = event.button().name
        if button_name is None:
            log.warning(f"Unknown mouse button: \"{button_name}\"")
            return
        self.on_mouse_button_event(int(pos.x()), int(pos.y()), button_name, InputState.pressed)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        button_name = event.button().name
        if button_name is None:
            log.warning(f"Unknown mouse button: \"{button_name}\"")
            return
        self.on_mouse_button_event(int(pos.x()), int(pos.y()), button_name, InputState.released)

    def wheelEvent(self, event: QWheelEvent) -> None:
        self.mods_manager.mouse_scroll.x += event.angleDelta().x()
        self.mods_manager.mouse_scroll.y += event.angleDelta().y()

        pos = event.position()
        x = int(pos.x())
        y = int(pos.y())

        for cmd in reversed(self.draw_commands):
            hit_id = cmd[-1]
            if hit_id is None:
                continue
            if self._hit_test(cmd, x, y):
                self.mods_manager.mouse_scroll.hit_id = hit_id
                break

    def on_mouse_button_event(self, x: int, y: int, button: str, button_state: InputState) -> None:
        if button not in self.mods_manager.mouse_events or button_state == InputState.pressed:
            pressed_at = time.time()
        else:
            pressed_at = self.mods_manager.mouse_events[button].pressed_at
        released_at = time.time() if button_state == InputState.released else None
        
        event = MouseButtonEvent(
            state=button_state,
            x=x,
            y=y,
            pressed_at=pressed_at,
            released_at=released_at,
            hit_id=None,
        )
        self.mods_manager.mouse_events[button] = event
        
        for cmd in reversed(self.draw_commands):
            hit_id = cmd[-1]
            if hit_id is None:
                continue
            if self._hit_test(cmd, x, y):
                self.mods_manager.mouse_events[button].hit_id = hit_id
                if button_state == InputState.pressed:
                    self.mods_manager.select_entity(hit_id)
                break

    @staticmethod
    def _hit_test(cmd: list, x: int, y: int) -> bool:
        alpha_hit_threshold = 10
        kind = cmd[0]

        if kind == "rect":
            _, rx, ry, rw, rh, color, filled, _hit_id = cmd
            if not (rx <= x <= rx + rw and ry <= y <= ry + rh):
                return False
            if filled and color.alpha() <= alpha_hit_threshold:
                return False
            return True

        elif kind == "line":
            _, x1, y1, x2, y2, color, width, hit_id = cmd
            return False # TODO: Dodaj sprawdzanie linii

        elif kind == "image":
            _, ix, iy, iw, ih, pixmap, _opacity, alpha_image, _hit_id = cmd
            w = iw if iw is not None else pixmap.width()
            h = ih if ih is not None else pixmap.height()
            if w <= 0 or h <= 0 or not (ix <= x <= ix + w and iy <= y <= iy + h):
                return False

            img_x = int((x - ix) / w * alpha_image.width())
            img_y = int((y - iy) / h * alpha_image.height())
            img_x = min(max(img_x, 0), alpha_image.width() - 1)
            img_y = min(max(img_y, 0), alpha_image.height() - 1)

            return alpha_image.pixelColor(img_x, img_y).alpha() > alpha_hit_threshold

        return False

class OverlayManager(QApplication):
    def __init__(self, conn, shared_data: SharedState):
        super().__init__(sys.argv)

        self.conn = conn
        self.shared_data: SharedState = shared_data

        self.watcher = WindowsWatcher()
        self.watcher.start()
        self.transparent_windows: dict[int, TransparentWindow] = {}
        self.draw_commands: dict[int, list] = {} # "hwnd": [["draw_rect"...], ["draw_image"...]...]

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
        self.shared_data.pull()
        self.process_timer.start("tick")
        # --- Obliczenie Delta Time ---
        now = time.perf_counter()
        self.dt = now - self._last_tick_time
        self._last_tick_time = now
        
        self.process_timer.start("check IPC")
        self._handle_ipc_commands()
        self.process_timer.stop("check IPC")

        self.watcher.clear_cache()
        
        self.process_timer.start("entities tick")
        self.draw_commands.clear()
        self.mods_manager.tick()
        self.process_timer.stop("entities tick")
        
        self.process_timer.start("update z-order")
        # Creating and updating z-order `TransparentWindow`
        if self.draw_commands:
            hdwp = self.user32.BeginDeferWindowPos(len(self.draw_commands))
            flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
            for hwnd in self.draw_commands.keys():
                if hwnd not in self.transparent_windows:
                    self.transparent_windows[hwnd] = TransparentWindow(hwnd, self.mods_manager)
                    title = win32gui.GetWindowText(hwnd)
                    log.debug(f'A new layer has been created on the window {hwnd} ({title})')

                neighbors: WindowNeighbors | None = self.watcher._windows_cache.get(hwnd, None)
                if neighbors is None or not isinstance(neighbors.window_above, int):
                    self.watcher.get_window_above(hwnd)
                hdwp = self.user32.DeferWindowPos(hdwp, self.transparent_windows[hwnd].hwnd_self, self.watcher._windows_cache[hwnd].window_above, 0, 0, 0, 0, flags)
            self.user32.EndDeferWindowPos(hdwp)

        # Deleting a `TransparentWindow` if the window assigned to it does not exist
        for hwnd in list(self.transparent_windows):
            if hwnd not in self.draw_commands:
                title = win32gui.GetWindowText(hwnd)
                log.debug(f'Removed layer assigned to hwnd {hwnd} ({title})')
                self.transparent_windows[hwnd].close()
                del self.transparent_windows[hwnd]
        self.process_timer.stop("update z-order")

        self.process_timer.start("windows paint_tick")
        for hwnd, draw_commands in self.draw_commands.items():
            self.transparent_windows[hwnd].draw_commands = draw_commands
        for window in self.transparent_windows.values():
            window.repaint()
        self.process_timer.stop("windows paint_tick")

        self.process_timer.stop("tick")

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
                if msg[0] == "close_app":
                    self.watcher.stop()
                    QCoreApplication.quit()
                elif msg[0] == "spawn_entity":
                    self.mods_manager.spawn_entity(msg[1], msg[2])
                elif msg[0] == "kill_entity":
                    self.mods_manager.kill_entity(msg[1])
                elif msg[0] == "show_entity":
                    self.mods_manager.show_entity(msg[1])
                elif msg[0] == "hide_entity":
                    self.mods_manager.hide_entity(msg[1])
                elif msg[0] == "teleport_entity":
                    self.mods_manager.teleport_entity(msg[1])
                elif msg[0] == "kill_all_entities":
                    self.mods_manager.kill_all_entities()
                elif msg[0] == "show_all_entities":
                    self.mods_manager.show_all_entities()
                elif msg[0] == "hide_all_entities":
                    self.mods_manager.hide_all_entities()
                else:
                    log.error(f"Unknown command: {msg}")
            else:
                return

def run_app(conn, shared_data: SharedState, log_queue):
    logger.init_child(log_queue)
    log.info("Starting the DESKTOP process...")
    app = OverlayManager(conn, shared_data)
    sys.exit(app.exec())
