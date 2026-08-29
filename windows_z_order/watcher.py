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

@dataclass
class WatchWindow:
    """Stores information about which neighbors of a given window to retrieve"""
    target_hwnd: int
    get_real_window_above: bool = True
    get_real_window_below: bool = True
    get_window_above: bool = True
    get_window_below: bool = True

    def __post_init__(self):
        if not (self.get_window_above or self.get_window_below):
            raise ValueError("The `get_window_above` or 'get_window_below' field must be True.")
        
        if self.get_real_window_above and not self.get_window_above:
            raise ValueError("The 'get_window_above' field must be True when 'get_real_window_above' is set to True.")

        if self.get_real_window_below and not self.get_window_below:
            raise ValueError("The 'get_window_below' field must be True when 'get_real_window_below' is set to True.")

@dataclass
class WindowNeighbors:
    """Stores the HWND of adjacent windows"""
    real_window_above: int | None
    real_window_below: int | None
    window_above: int | None
    window_below: int | None

class NeighborsWatcher:
    """Listens for changes in z-order and then updates the nearest neighbors (above/below) of the given windows.

    Use:
        watcher = NeighborsWatcher()
        watcher.start()
        ...
        watcher.update_neighbor_windows(hwnd_list)
        window = watcher.neighbor_windows[target_hwnd]
        print(window.window_above, window.real_window_below)
        ...
        watcher.stop()
    """
    def __init__(self) -> None:
        self.neighbor_windows: dict[int, WindowNeighbors] = {}
        self.old_neighbor_windows: dict[int, WindowNeighbors] = {}
        self._lock = threading.Lock()
        self._started = threading.Event()
        self._thread: threading.Thread | None = None
        self._thread_id: int | None = None
        self._callback = _WinEventProcType(self._on_event)
        
        self.changes_detected: bool = True

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
    
    def __enter__(self) -> "NeighborsWatcher":
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
        if not hook_a or not hook_b:
            if hook_a:
                _user32.UnhookWinEvent(hook_a)
            if hook_b:
                _user32.UnhookWinEvent(hook_b)
            raise OSError("SetWinEventHook failed")

        try:
            win32gui.PumpMessages() # blocks until WM_QUIT (see stop())
        finally:
            _user32.UnhookWinEvent(hook_a)
            _user32.UnhookWinEvent(hook_b)

    def _on_event(self, hook, event, hwnd, id_object, id_child, id_thread, event_time):
        try:
            if id_object != OBJID_WINDOW or id_child != CHILDID_SELF:
                return
            self.changes_detected = True
        except Exception:
            pass

    # -- public API ----------------------------------------------------------
    
    def update_neighbor_windows(self, target_windows: list[WatchWindow | int]) -> None:
        """Updates variables and fetches neighboring windows only if changes are detected"""
        with self._lock:
            if not self.changes_detected:
                return
            self.changes_detected = False

            old = self.neighbor_windows
            new_neighbors: dict[int, WindowNeighbors] = {}
            for window in target_windows:
                if isinstance(window, int):
                    window = WatchWindow(window)

                # TODO: To się da zoptymalizować mapując z-index okien (Coś podobnego już jest w obiektach, gdzie obiekty które są na wspólnym oknie pobierają sąsiednie okna tylko raz)
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

                new_neighbors[window.target_hwnd] = WindowNeighbors(
                    real_window_above=real_above,
                    real_window_below=real_below,
                    window_above=above,
                    window_below=below,
                )

            self.old_neighbor_windows = old
            self.neighbor_windows = new_neighbors

def main():
    hwnd_input: str = input("Enter window hwnd: ")
    if hwnd_input == "":
        target_hwnd: int = win32gui.GetForegroundWindow()
    elif hwnd_input.isdigit():
        target_hwnd = int(hwnd_input)
    else:
        target_hwnd = win32gui.FindWindow(None, hwnd_input)
    print(f"\nHWND: {target_hwnd} ({win32gui.GetWindowText(target_hwnd)})")

    watcher = NeighborsWatcher()
    watcher.start()
    try:
        while True:
            if watcher.changes_detected:
                watcher.update_neighbor_windows([target_hwnd])
                window_neighbors = watcher.neighbor_windows[target_hwnd]
                old_window_neighbors = watcher.old_neighbor_windows.get(target_hwnd, WindowNeighbors(None, None, None, None))
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
