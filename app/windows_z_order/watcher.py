"""Win32 event listener (SetWinEventHook) that watches z-order, geometry, title and state changes of windows and serves cached answers."""
import ctypes
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import cast

import win32api
import win32con
import win32gui

from app.windows_z_order.neighbors import get_real_window_above, get_real_window_below, get_window_above, get_window_below
from app.desktop.physics_utils import XYXY_Rectangle

# ---------------------------------------------------------------------------
# Constants WinEvent (winuser.h)
# ---------------------------------------------------------------------------

EVENT_SYSTEM_FOREGROUND     = 0x0003
EVENT_SYSTEM_MOVESIZESTART  = 0x000A
EVENT_SYSTEM_MOVESIZEEND    = 0x000B
EVENT_SYSTEM_MINIMIZESTART  = 0x0016
EVENT_SYSTEM_MINIMIZEEND    = 0x0017
EVENT_OBJECT_CREATE         = 0x8000
EVENT_OBJECT_DESTROY        = 0x8001
EVENT_OBJECT_SHOW           = 0x8002
EVENT_OBJECT_HIDE           = 0x8003
EVENT_OBJECT_REORDER        = 0x8004
EVENT_OBJECT_LOCATIONCHANGE = 0x800B
EVENT_OBJECT_NAMECHANGE     = 0x800C

WINEVENT_OUTOFCONTEXT = 0x0000
OBJID_WINDOW = 0
CHILDID_SELF = 0

_user32 = ctypes.windll.user32

_WinEventProcType = ctypes.WINFUNCTYPE(
    None,
    wintypes.HANDLE,   # hWinEventHook
    wintypes.DWORD,    # event
    wintypes.HWND,     # hwnd
    wintypes.LONG,     # idObject
    wintypes.LONG,     # idChild
    wintypes.DWORD,    # idEventThread
    wintypes.DWORD,    # dwmsEventTime
)

_user32.SetWinEventHook.restype = wintypes.HANDLE
_user32.SetWinEventHook.argtypes = [
    wintypes.UINT, wintypes.UINT,
    wintypes.HMODULE, _WinEventProcType,
    wintypes.DWORD, wintypes.DWORD, wintypes.UINT,
]
_user32.UnhookWinEvent.restype = wintypes.BOOL
_user32.UnhookWinEvent.argtypes = [wintypes.HANDLE]

# Sentinel distinguishing "never fetched" from the legal value `None`
# (e.g., the window at the very top/bottom of the z-order has no neighbor -> the result is `None`)
_MISSING: object = object()

@dataclass
class WindowNeighbors:
    """Single window cache: neighbors (above/below, real and fake)."""
    real_window_above: int | None | object = _MISSING
    window_above: int | None | object = _MISSING
    real_window_below: int | None | object = _MISSING
    window_below: int | None | object = _MISSING

class WindowsWatcher:
    """Listens for changes in z-order and window geometry, and lazily caches
    neighbor (above/below) and rect information for individual windows on request.

    Use:
        watcher = WindowsWatcher()
        watcher.start()
        ...
        watcher.clear_cache()  # no-op unless z-order changed since last call
        above = watcher.get_window_above(target_hwnd)
        rect = watcher.get_window_rect(target_hwnd)
        title = watcher.get_window_title(target_hwnd)
        ...
        watcher.stop()
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = threading.Event()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._start_error: BaseException | None = None
        self._callback = _WinEventProcType(self._on_event)
        self._location_callback = _WinEventProcType(self._on_location_or_name_event)

        # Neighbors cache (above/below); fully cleared by clear_cache, but only if the z-order actually changed.
        self._window_neighbors_cache: dict[int, WindowNeighbors] = {}
        self._z_order_changes_detected: bool = True

        self._rect_cache: dict[int, XYXY_Rectangle | None] = {}
        self._title_cache: dict[int, str] = {}
        self._foreground_window_cache: int | None = None
        self._window_exists_cache: dict[int, bool] = {}
        self._visible_window_cache: dict[int, bool] = {}
        self._minimized_window_cache: dict[int, bool] = {}
        self._maximized_window_cache: dict[int, bool] = {}
        self._fullscreen_window_cache: dict[int, bool] = {}

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Starts listening. Returns once the hooks are installed; raises if they could not be installed."""
        if self._thread is not None:
            return
        self._started.clear()
        self._start_error = None
        self._thread = threading.Thread(target=self._run, name="WindowsWatcher", daemon=True)
        self._thread.start()
        if not self._started.wait(timeout=5.0):
            raise TimeoutError("WindowsWatcher thread did not start")
        if self._start_error is not None:
            error = self._start_error
            self._thread.join(timeout=2.0)
            self._thread = None
            raise error

    def stop(self) -> None:
        """Stops listening"""
        if self._thread is None:
            return
        self._started.wait(timeout=2.0)
        if self._thread_id is not None:
            try:
                win32api.PostThreadMessage(self._thread_id, win32con.WM_QUIT, 0, 0)
            except Exception:
                pass
        self._thread.join(timeout=2.0)
        self._thread = None
        self._thread_id = None
        self._started.clear()

    def __enter__(self) -> "WindowsWatcher":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # -- listening thread ---------------------------------------------------

    def _run(self) -> None:
        self._thread_id = win32api.GetCurrentThreadId()
        msg = wintypes.MSG()
        _user32.PeekMessageW(ctypes.byref(msg), None, win32con.WM_USER, win32con.WM_USER, win32con.PM_NOREMOVE)

        hook_a = _user32.SetWinEventHook(EVENT_SYSTEM_FOREGROUND, EVENT_SYSTEM_MINIMIZEEND, 0, self._callback, 0, 0, WINEVENT_OUTOFCONTEXT)
        hook_b = _user32.SetWinEventHook(EVENT_OBJECT_CREATE, EVENT_OBJECT_REORDER, 0, self._callback, 0, 0, WINEVENT_OUTOFCONTEXT)
        hook_c = _user32.SetWinEventHook(EVENT_OBJECT_LOCATIONCHANGE, EVENT_OBJECT_NAMECHANGE, 0, self._location_callback, 0, 0, WINEVENT_OUTOFCONTEXT)
        if not hook_a or not hook_b or not hook_c:
            if hook_a:
                _user32.UnhookWinEvent(hook_a)
            if hook_b:
                _user32.UnhookWinEvent(hook_b)
            if hook_c:
                _user32.UnhookWinEvent(hook_c)
            self._start_error = OSError("SetWinEventHook failed")
            self._started.set()
            return

        self._started.set()
        try:
            win32gui.PumpMessages() # blocks until WM_QUIT (see stop())
        finally:
            _user32.UnhookWinEvent(hook_a)
            _user32.UnhookWinEvent(hook_b)
            _user32.UnhookWinEvent(hook_c)

    def _on_event(self, hook, event, hwnd, id_object, id_child, id_thread, event_time):
        """Handles z-order-relevant events (foreground/create/destroy/reorder/...)."""
        if id_object != OBJID_WINDOW or id_child != CHILDID_SELF:
            return
        if event == EVENT_OBJECT_DESTROY and hwnd:
            with self._lock:
                for cache in (self._rect_cache, self._title_cache, self._maximized_window_cache, self._fullscreen_window_cache):
                    cache.pop(hwnd, None)
                self._window_exists_cache[hwnd] = False
        self._z_order_changes_detected = True

    def _on_location_or_name_event(self, hook, event, hwnd, id_object, id_child, id_thread, event_time):
        """Handles EVENT_OBJECT_LOCATIONCHANGE and EVENT_OBJECT_NAMECHANGE"""
        try:
            if id_object != OBJID_WINDOW or id_child != CHILDID_SELF:
                return
            with self._lock:
                if event == EVENT_OBJECT_LOCATIONCHANGE:
                    self._rect_cache.pop(hwnd, None)
                    self._maximized_window_cache.pop(hwnd, None)
                    self._fullscreen_window_cache.pop(hwnd, None)
                elif event == EVENT_OBJECT_NAMECHANGE:
                    self._title_cache.pop(hwnd, None)
        except Exception:
            pass

    # -- public API ----------------------------------------------------------

    def clear_cache(self) -> None:
        """Invalidates the neighbor cache and the foreground/exists/visible/minimized/maximized/fullscreen caches,
        but only if the z-order changed since the last call."""
        with self._lock:
            if not self._z_order_changes_detected:
                return
            self._z_order_changes_detected = False
            self._window_neighbors_cache.clear()

            self._foreground_window_cache = None
            self._window_exists_cache.clear()
            self._visible_window_cache.clear()
            self._minimized_window_cache.clear()
            self._maximized_window_cache.clear()
            self._fullscreen_window_cache.clear()

    def get_real_window_above(self, hwnd: int) -> tuple[int | None, int | None]:
        """Returns the nearest real (non-transparent/non-tool) window above `hwnd`."""
        with self._lock:
            entry = self._window_neighbors_cache.get(hwnd)
            if entry is not None and entry.real_window_above is not _MISSING and entry.window_above is not _MISSING:
                return cast(int | None, entry.real_window_above), cast(int | None, entry.window_above)

        real_above, above = get_real_window_above(hwnd)

        with self._lock:
            entry = self._window_neighbors_cache.setdefault(hwnd, WindowNeighbors())
            entry.real_window_above = real_above
            entry.window_above = above
        return real_above, above

    def get_window_above(self, hwnd: int) -> int | None:
        """Returns the window immediately above `hwnd` in z-order (may be a transparent/tool window)."""
        with self._lock:
            entry = self._window_neighbors_cache.get(hwnd)
            if entry is not None and entry.window_above is not _MISSING:
                return cast(int | None, entry.window_above)

        above = get_window_above(hwnd)

        with self._lock:
            entry = self._window_neighbors_cache.setdefault(hwnd, WindowNeighbors())
            entry.window_above = above
        return above

    def get_real_window_below(self, hwnd: int) -> tuple[int | None, int | None]:
        """Returns the nearest real (non-transparent/non-tool) window below `hwnd`."""
        with self._lock:
            entry = self._window_neighbors_cache.get(hwnd)
            if entry is not None and entry.real_window_below is not _MISSING and entry.window_below is not _MISSING:
                return cast(int | None, entry.real_window_below), cast(int | None, entry.window_below)

        real_below, below = get_real_window_below(hwnd)

        with self._lock:
            entry = self._window_neighbors_cache.setdefault(hwnd, WindowNeighbors())
            entry.real_window_below = real_below
            entry.window_below = below
        return real_below, below

    def get_window_below(self, hwnd: int) -> int | None:
        """Returns the window immediately below `hwnd` in z-order (may be a transparent/tool window)."""
        with self._lock:
            entry = self._window_neighbors_cache.get(hwnd)
            if entry is not None and entry.window_below is not _MISSING:
                return cast(int | None, entry.window_below)

        below = get_window_below(hwnd)

        with self._lock:
            entry = self._window_neighbors_cache.setdefault(hwnd, WindowNeighbors())
            entry.window_below = below
        return below

    def get_window_rect(self, hwnd: int) -> XYXY_Rectangle | None:
        """Returns the geometry of `hwnd` or None if the window does not exist."""
        if not self.window_exists(hwnd):
            return None
        with self._lock:
            if hwnd not in self._rect_cache:
                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                rect = XYXY_Rectangle(left, top, right, bottom)
                self._rect_cache[hwnd] = rect
            return self._rect_cache[hwnd]

    def get_window_title(self, hwnd: int) -> str | None:
        """Returns the title of `hwnd` or None if the window does not exist."""
        if not self.window_exists(hwnd):
            return None
        with self._lock:
            if hwnd not in self._title_cache:
                self._title_cache[hwnd] = win32gui.GetWindowText(hwnd)
            return self._title_cache[hwnd]

    def get_foreground_window_hwnd(self) -> int:
        """Returns the hwnd of the foreground (focused) window (0 if there is none)."""
        with self._lock:
            if self._foreground_window_cache is None:
                self._foreground_window_cache = win32gui.GetForegroundWindow()
            return self._foreground_window_cache

    def is_window_foreground(self, hwnd: int) -> bool | None:
        """Returns whether `hwnd` is the foreground (focused) window or None if the window does not exist."""
        if not self.window_exists(hwnd):
            return None
        return self.get_foreground_window_hwnd() == hwnd

    def window_exists(self, hwnd: int) -> bool:
        """Returns whether `hwnd` is still a valid window."""
        with self._lock:
            if hwnd not in self._window_exists_cache:
                self._window_exists_cache[hwnd] =  bool(win32gui.IsWindow(hwnd))
            return self._window_exists_cache[hwnd]

    def is_window_visible(self, hwnd: int) -> bool | None:
        """Returns whether `hwnd` has the visible style (minimized windows count as visible), None if it does not exist."""
        if not self.window_exists(hwnd):
            return None
        with self._lock:
            if hwnd not in self._visible_window_cache:
                self._visible_window_cache[hwnd] = bool(win32gui.IsWindowVisible(hwnd))
            return self._visible_window_cache[hwnd]

    def is_window_minimized(self, hwnd: int) -> bool | None:
        """Returns whether `hwnd` is minimized or None if the window does not exist."""
        if not self.window_exists(hwnd):
            return None
        with self._lock:
            if hwnd not in self._minimized_window_cache:
                self._minimized_window_cache[hwnd] = bool(win32gui.IsIconic(hwnd))
            return self._minimized_window_cache[hwnd]

    def is_window_maximized(self, hwnd: int) -> bool | None:
        """Returns whether `hwnd` is maximized or None if the window does not exist."""
        if not self.window_exists(hwnd):
            return None
        with self._lock:
            if hwnd not in self._maximized_window_cache:
                self._maximized_window_cache[hwnd] = bool(win32gui.IsZoomed(hwnd))
            return self._maximized_window_cache[hwnd]

    def is_window_fullscreen(self, hwnd: int) -> bool | None:
        """Returns whether `hwnd` covers its whole monitor including the taskbar, None if it does not exist."""
        rect = self.get_window_rect(hwnd)
        if rect is None:
            return None
        with self._lock:
            if hwnd not in self._fullscreen_window_cache:
                monitor = win32api.MonitorFromWindow(hwnd, win32con.MONITOR_DEFAULTTONEAREST)
                m = win32api.GetMonitorInfo(monitor)["Monitor"]
                self._fullscreen_window_cache[hwnd] = rect[0] <= m[0] and rect[1] <= m[1] and rect[2] >= m[2] and rect[3] >= m[3]
            return self._fullscreen_window_cache[hwnd]

def main() -> None:
    hwnd_input: str = input("Enter window hwnd: ")
    if hwnd_input == "":
        target_hwnd: int = win32gui.GetForegroundWindow()
    elif hwnd_input.isdigit():
        target_hwnd = int(hwnd_input)
    else:
        target_hwnd = win32gui.FindWindow(None, hwnd_input)
    print(f"\nHWND: {target_hwnd} ({win32gui.GetWindowText(target_hwnd)})")

    watcher = WindowsWatcher()
    watcher.start()
    previous_windows: tuple[int | None, int | None, int | None, int | None] = (None, None, None, None)
    try:
        while True:
            watcher.clear_cache()

            real_above, above = watcher.get_real_window_above(target_hwnd)
            real_below, below = watcher.get_real_window_below(target_hwnd)
            current_windows = (above, below, real_above, real_below)

            width: int = 40
            window_titles = f" ({',  '.join([(t if (t := win32gui.GetWindowText(hwnd)) else 'None') if hwnd else 'None' for hwnd in current_windows])})"
            if previous_windows != current_windows:
                if previous_windows[:2] != current_windows[:2] and previous_windows[2:] == current_windows[2:]:
                    print("Change detected only in fake windows:".ljust(width), f"{current_windows}".ljust(width) + window_titles)
                elif previous_windows[:2] == current_windows[:2] and previous_windows[2:] != current_windows[2:]:
                    print("Change detected only in real windows:".ljust(width), f"{current_windows}".ljust(width) + window_titles)
                else:
                    print("Change detected:".ljust(width), f"{current_windows}".ljust(width) + window_titles)
                previous_windows = current_windows
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()

if __name__ == "__main__":
    main()
