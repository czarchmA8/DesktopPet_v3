"""Win32 event listener (SetWinEventHook) listening for in z-order changes and then updates the nearest neighbors (above/below) of the given windows"""
import ctypes
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from typing import cast

import win32api
import win32con
import win32gui

from windows_z_order.neighbors import get_real_window_above, get_real_window_below, get_window_above, get_window_below
from desktop.physics_utils import XYXY_Rectangle

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

# Sentinel distinguishing "never downloaded" from the legal value `None`
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
        self._callback = _WinEventProcType(self._on_event)
        self._location_callback = _WinEventProcType(self._on_location_or_name_event)

        # Neighbors cache (above/below); fully cleared by clear_cache, but only if the z-order actually changed.
        self._windows_cache: dict[int, WindowNeighbors] = {}
        self._z_order_changes_detected: bool = True

        # Window geometry cache; cleared individually per-hwnd only if a size/position changed for that window.
        self._rect_cache: dict[int, XYXY_Rectangle] = {}
        self._resized_windows: set[int] = set()

        # Window title cache; cleared individually per-hwnd only if title changes for that window
        self._title_cache: dict[int, str] = {}
        self._changed_title_windows: set[int] = set()

    # -- lifecycle ----------------------------------------------------------

    def start(self) -> None:
        """Starts listening"""
        if self._thread is not None:
            return
        self._thread = threading.Thread(target=self._run, name="NeighborsWatcher", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stops listening"""
        if self._thread is None:
            return
        self._started.wait(timeout=2.0)
        if self._thread_id is not None:
            win32api.PostThreadMessage(self._thread_id, win32con.WM_QUIT, 0, 0)
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
        self._started.set()

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
            raise OSError("SetWinEventHook failed")

        try:
            win32gui.PumpMessages() # blocks until WM_QUIT (see stop())
        finally:
            _user32.UnhookWinEvent(hook_a)
            _user32.UnhookWinEvent(hook_b)
            _user32.UnhookWinEvent(hook_c)

    def _on_event(self, hook, event, hwnd, id_object, id_child, id_thread, event_time):
        """Handles z-order-relevant events (foreground/create/destroy/reorder/...)."""
        try:
            if id_object != OBJID_WINDOW or id_child != CHILDID_SELF:
                return
            self._z_order_changes_detected = True
        except Exception:
            pass

    def _on_location_or_name_event(self, hook, event, hwnd, id_object, id_child, id_thread, event_time):
        """Handles EVENT_OBJECT_LOCATIONCHANGE and EVENT_OBJECT_NAMECHANGE"""
        try:
            if id_object != OBJID_WINDOW or id_child != CHILDID_SELF:
                return
            with self._lock:
                if event == EVENT_OBJECT_LOCATIONCHANGE:
                    self._resized_windows.add(hwnd)
                elif event == EVENT_OBJECT_NAMECHANGE:
                    self._changed_title_windows.add(hwnd)
        except Exception:
            pass

    # -- public API ----------------------------------------------------------

    def clear_cache(self) -> None:
        """Invalidates the neighbor cache, but only if a z-order changes."""
        with self._lock:
            if not self._z_order_changes_detected:
                return
            self._z_order_changes_detected = False
            self._windows_cache.clear()

    def get_real_window_above(self, hwnd: int) -> tuple[int | None, int | None]:
        """Returns the nearest real (non-transparent/non-tool) window above `hwnd`."""
        with self._lock:
            entry = self._windows_cache.get(hwnd)
            if entry is not None and entry.real_window_above is not _MISSING and entry.window_above is not _MISSING:
                return cast(int | None, entry.real_window_above), cast(int | None, entry.window_above)

        real_above, above = get_real_window_above(hwnd)

        with self._lock:
            entry = self._windows_cache.setdefault(hwnd, WindowNeighbors())
            entry.real_window_above = real_above
            entry.window_above = above
        return real_above, above

    def get_window_above(self, hwnd: int) -> int | None:
        """Returns the window immediately above `hwnd` in z-order (may be a transparent/tool window)."""
        with self._lock:
            entry = self._windows_cache.get(hwnd)
            if entry is not None and entry.window_above is not _MISSING:
                return cast(int | None, entry.window_above)

        above = get_window_above(hwnd)

        with self._lock:
            entry = self._windows_cache.setdefault(hwnd, WindowNeighbors())
            entry.window_above = above
        return above

    def get_real_window_below(self, hwnd: int) -> tuple[int | None, int | None]:
        """Returns the nearest real (non-transparent/non-tool) window below `hwnd`."""
        with self._lock:
            entry = self._windows_cache.get(hwnd)
            if entry is not None and entry.real_window_below is not _MISSING and entry.window_below is not _MISSING:
                return cast(int | None, entry.real_window_below), cast(int | None, entry.window_below)

        real_below, below = get_real_window_below(hwnd)

        with self._lock:
            entry = self._windows_cache.setdefault(hwnd, WindowNeighbors())
            entry.real_window_below = real_below
            entry.window_below = below
        return real_below, below

    def get_window_below(self, hwnd: int) -> int | None:
        """Returns the window immediately below `hwnd` in z-order (may be a transparent/tool window)."""
        with self._lock:
            entry = self._windows_cache.get(hwnd)
            if entry is not None and entry.window_below is not _MISSING:
                return cast(int | None, entry.window_below)

        below = get_window_below(hwnd)

        with self._lock:
            entry = self._windows_cache.setdefault(hwnd, WindowNeighbors())
            entry.window_below = below
        return below

    def get_window_rect(self, hwnd: int) -> XYXY_Rectangle:
        """Returns the geometry of `hwnd`."""
        with self._lock:
            needs_refresh = hwnd not in self._rect_cache or hwnd in self._resized_windows
            if not needs_refresh:
                return self._rect_cache[hwnd]
            self._resized_windows.discard(hwnd)

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        rect = XYXY_Rectangle(left, top, right, bottom)

        with self._lock:
            self._rect_cache[hwnd] = rect
        return rect

    def get_window_title(self, hwnd: int) -> str:
        """Returns the title of `hwnd`."""
        with self._lock:
            needs_refresh = hwnd not in self._title_cache or hwnd in self._changed_title_windows
            if not needs_refresh:
                return self._title_cache[hwnd]
            self._changed_title_windows.discard(hwnd)

        title = win32gui.GetWindowText(hwnd)

        with self._lock:
            self._title_cache[hwnd] = title
        return title

    def get_foreground_window_hwnd(self) -> int:
        return win32gui.GetForegroundWindow()

def main():
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
    previous_windows = (None, None, None, None)
    try:
        while True:
            watcher.clear_cache()

            above = watcher.get_window_above(target_hwnd)
            below = watcher.get_window_below(target_hwnd)
            real_above = watcher.get_real_window_above(target_hwnd)
            real_below = watcher.get_real_window_below(target_hwnd)
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
