"""Win32 event listener (SetWinEventHook) listening for in z-order changes and then updates the nearest neighbors (above/below) of the given windows"""
import ctypes
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass

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

@dataclass(frozen=True)
class WatchWindow:
    """Stores information about which neighbors of a given window to retrieve"""
    target_hwnd: int
    get_real_window_above: bool = True
    get_real_window_below: bool = True
    get_window_above: bool = True
    get_window_below: bool = True
    get_window_rect: bool = True

    def __post_init__(self):
        if not (self.get_window_above or self.get_window_below):
            raise ValueError("The `get_window_above` or 'get_window_below' field must be True.")
        
        if self.get_real_window_above and not self.get_window_above:
            raise ValueError("The 'get_window_above' field must be True when 'get_real_window_above' is set to True.")

        if self.get_real_window_below and not self.get_window_below:
            raise ValueError("The 'get_window_below' field must be True when 'get_real_window_below' is set to True.")

@dataclass
class WatchedWindow:
    """Stores the HWND of adjacent windows"""
    real_window_above: int | None = None
    real_window_below: int | None = None
    window_above: int | None = None
    window_below: int | None = None
    rect: XYXY_Rectangle | None = None

class WindowsWatcher:
    """Listens for changes in z-order and then updates the nearest neighbors (above/below) of the given windows.

    Use:
        watcher = NeighborsWatcher()
        watcher.start()
        ...
        watcher.update_info_in_watched_windows(hwnd_list)
        window = watcher.watched_windows[target_hwnd]
        print(window.window_above, window.real_window_below)
        ...
        watcher.stop()
    """
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started = threading.Event()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._callback = _WinEventProcType(self._on_event)
        self._location_callback = _WinEventProcType(self._on_location_event)

        self.watched_windows: dict[int, WatchedWindow] = {}
        self.old_watched_windows: dict[int, WatchedWindow] = {}
        self.old_target_windows: set[WatchWindow] = set()
        
        self._z_order_changes_detected: bool = True
        self._resized_windows: set[int] = set()

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
        hook_c = _user32.SetWinEventHook(EVENT_OBJECT_LOCATIONCHANGE, EVENT_OBJECT_LOCATIONCHANGE, 0, self._location_callback, 0, 0, WINEVENT_OUTOFCONTEXT)
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

    def _on_location_event(self, hook, event, hwnd, id_object, id_child, id_thread, event_time):
        """Handles EVENT_OBJECT_LOCATIONCHANGE"""
        try:
            if id_object != OBJID_WINDOW or id_child != CHILDID_SELF:
                return
            with self._lock:
                self._resized_windows.add(hwnd)
        except Exception:
            pass

    # -- public API ----------------------------------------------------------

    def update_info_in_watched_windows(self, target_windows: set[WatchWindow]) -> None:
        """Updates variables and fetches neighboring windows only if changes are detected"""
        with self._lock:
            if self.old_target_windows != target_windows:
                added_elements = target_windows - self.old_target_windows
            else:
                added_elements = set()

            z_order_changed = self._z_order_changes_detected
            self.old_watched_windows = self.watched_windows.copy()
            
            if z_order_changed: # Updating all window neighbors on z-order change
                self._z_order_changes_detected = False

                new_watched_windows: dict[int, WatchedWindow] = {}
                for window in target_windows:
                    # TODO: To się da zoptymalizować mapując z-index okien (Coś podobnego już jest w obiektach, gdzie obiekty które są na wspólnym oknie pobierają sąsiednie okna tylko raz)
                    real_above = above = real_below = below = None
                    if window.get_window_above:
                        if window.get_real_window_above:
                            real_above, above = get_real_window_above(window.target_hwnd)
                        else:
                            real_above = None
                            above = get_window_above(window.target_hwnd)
                    if window.get_window_below:
                        if window.get_real_window_below:
                            real_below, below = get_real_window_below(window.target_hwnd)
                        else:
                            real_below = None
                            below = get_window_below(window.target_hwnd)
                    if window.get_window_rect:
                        if window.target_hwnd in self.old_watched_windows and window.target_hwnd not in self._resized_windows:
                            xyxy_rect = self.old_watched_windows[window.target_hwnd].rect
                            if xyxy_rect is None:
                                left, top, right, bottom = win32gui.GetWindowRect(window.target_hwnd)
                                xyxy_rect = XYXY_Rectangle(left, top, right, bottom)
                        else:
                            left, top, right, bottom = win32gui.GetWindowRect(window.target_hwnd)
                            xyxy_rect = XYXY_Rectangle(left, top, right, bottom)
                    else:
                        xyxy_rect = None

                    new_watched_windows[window.target_hwnd] = WatchedWindow(
                        real_window_above=real_above,
                        real_window_below=real_below,
                        window_above=above,
                        window_below=below,
                        rect=xyxy_rect,
                    )

                self.watched_windows = new_watched_windows
            elif added_elements: # Adding information about neighbors only in new windows
                for window in added_elements:
                    real_above = above = real_below = below = None
                    if window.get_window_above:
                        if window.get_real_window_above:
                            real_above, above = get_real_window_above(window.target_hwnd)
                        else:
                            real_above = None
                            above = get_window_above(window.target_hwnd)
                    if window.get_window_below:
                        if window.get_real_window_below:
                            real_below, below = get_real_window_below(window.target_hwnd)
                        else:
                            real_below = None
                            below = get_window_below(window.target_hwnd)
                    if window.get_window_rect:
                        left, top, right, bottom = win32gui.GetWindowRect(window.target_hwnd)
                        xyxy_rect = XYXY_Rectangle(left, top, right, bottom)
                    else:
                        xyxy_rect = None
                    
                    self.watched_windows[window.target_hwnd] = WatchedWindow(
                        real_window_above=real_above,
                        real_window_below=real_below,
                        window_above=above,
                        window_below=below,
                        rect=xyxy_rect,
                    )
            if (self._resized_windows or added_elements) and not z_order_changed: # Updating sizes and positions of only windows that have been changed or added. Skipping updating on `self._z_order_changes_detected` because the windows have already been updated
                resized_windows: set[WatchWindow] = set(window for window in target_windows if window.target_hwnd in self._resized_windows or window in added_elements)
                self._resized_windows.clear()

                for window in resized_windows:
                    if window.get_window_rect:
                        left, top, right, bottom = win32gui.GetWindowRect(window.target_hwnd)
                        xyxy_rect = XYXY_Rectangle(left, top, right, bottom)
                    else:
                        xyxy_rect = None

                    # Creating a new `WatchedWindow` object so that `self.old_watched_windows` does not update
                    existing_window = self.watched_windows[window.target_hwnd]
                    self.watched_windows[window.target_hwnd] = WatchedWindow(
                        real_window_above=existing_window.real_window_above,
                        real_window_below=existing_window.real_window_below,
                        window_above=existing_window.window_above,
                        window_below=existing_window.window_below,
                        rect=xyxy_rect,
                    )

            self.old_target_windows = target_windows.copy()

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
    try:
        while True:
            if watcher._z_order_changes_detected or watcher._resized_windows:
                watcher.update_info_in_watched_windows({WatchWindow(target_hwnd)})
                window_neighbors = watcher.watched_windows[target_hwnd]
                old_window_neighbors = watcher.old_watched_windows.get(target_hwnd, WatchedWindow(None, None, None, None, None))
                previous_windows = old_window_neighbors.window_above, old_window_neighbors.window_below, old_window_neighbors.real_window_above, old_window_neighbors.real_window_below
                current_windows = window_neighbors.window_above, window_neighbors.window_below, window_neighbors.real_window_above, window_neighbors.real_window_below
                width: int = 80
                window_titles = f" ({',  '.join([(t if (t := win32gui.GetWindowText(hwnd)) else 'None') if hwnd else 'None' for hwnd in current_windows])})"
                if previous_windows != current_windows:
                    if previous_windows[:2] != current_windows[:2] and previous_windows[2:] == current_windows[2:]:
                        print(f"Change detected only in fake windows: {current_windows}".ljust(width) + window_titles)
                    elif previous_windows[:2] == current_windows[:2] and previous_windows[2:] != current_windows[2:]:
                        print(f"Change detected only in real windows: {current_windows}".ljust(width) + window_titles)
                    else:
                        print(f"Change detected: {current_windows}".ljust(width) + window_titles)
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        pass
    finally:
        watcher.stop()

if __name__ == "__main__":
    main()
