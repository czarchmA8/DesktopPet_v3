import ctypes
from ctypes import wintypes
from functools import lru_cache
import os
import psutil
from typing import TypedDict
import win32con
import win32gui
import win32process

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class FilterList(TypedDict):
    BlackList: bool
    List: list[str]

List_Classes: FilterList   = {"BlackList": True,  "List": ["Progman", "Shell_TrayWnd"]}
List_Titles: FilterList    = {"BlackList": True,  "List": []}
List_exe_paths: FilterList = {"BlackList": True,  "List": []}

# ---------------------------------------------------------------------------
# Module-level DWM handle
# ---------------------------------------------------------------------------

_dwmapi = ctypes.WinDLL("dwmapi")
_DWMWA_CLOAKED = 14

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1024)
def _get_exe_name(hwnd: int) -> str:
    """Return the executable base-name for the process owning *hwnd*.

    Results are cached by hwnd.  Call clear_exe_cache() when windows are
    destroyed so stale entries (hwnd reuse by Windows) don't accumulate.
    """
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    return os.path.basename(psutil.Process(pid).exe())

def clear_exe_cache() -> None:
    """Invalidate the exe-name cache (call on window-destroy events)."""
    _get_exe_name.cache_clear()

def _is_cloaked(hwnd: int) -> bool:
    """Return True if the window is DWM-cloaked (hidden from the user)."""
    cloaked = wintypes.DWORD()
    result  = _dwmapi.DwmGetWindowAttribute(hwnd, _DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    return result == 0 and bool(cloaked.value)

# ---------------------------------------------------------------------------
# Main function
# ---------------------------------------------------------------------------

def is_real_window(hwnd: int) -> bool:
    """Return True if *hwnd* is a real, user-visible, top-level window.

    Checks are ordered from cheapest to most expensive so that the majority
    of system/hidden handles are rejected before any costly I/O happens.

    Tier 1 – cheap Win32 bool checks (no heap allocation)
    Tier 2 – title string (single alloc, needed for empty-check + filter)
    Tier 3 – DWM cloaked (module-level handle, one attribute query)
    Tier 4 – window rect (four integers)
    Tier 5 – class name + filter
    Tier 6 – title filter (string already in hand)
    Tier 7 – exe-name filter (lru_cache + psutil I/O, only when list is set)
    """

    # Tier 1 ----------------------------------------------------------------
    if not win32gui.IsWindowVisible(hwnd):          return False
    if win32gui.IsIconic(hwnd):                      return False
    if win32gui.GetWindow(hwnd, win32con.GW_OWNER):  return False

    # Tier 2 ----------------------------------------------------------------
    title = win32gui.GetWindowText(hwnd).strip()
    if not title:                                    return False

    # Tier 3 ----------------------------------------------------------------
    if _is_cloaked(hwnd):                            return False

    # Tier 4 ----------------------------------------------------------------
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    if (r - l) <= 1 or (b - t) <= 1:                return False

    # Tier 5 ----------------------------------------------------------------
    if List_Classes["List"]:
        cls = win32gui.GetClassName(hwnd)
        if (cls in List_Classes["List"]) == List_Classes["BlackList"]:
            return False

    # Tier 6 ----------------------------------------------------------------
    if List_Titles["List"]:
        if (title in List_Titles["List"]) == List_Titles["BlackList"]:
            return False

    # Tier 7 ----------------------------------------------------------------
    if List_exe_paths["List"]:
        try:
            exe = _get_exe_name(hwnd)
            if (exe in List_exe_paths["List"]) == List_exe_paths["BlackList"]:
                return False
        except Exception:
            pass

    return True

def get_immediate_neighbors_above_and_below(target_hwnd: int, only_real_windows: bool = True, blacklist_hwnd: list[int] | None = None) -> tuple[int | None, int | None]:
    """Gets the nearest visible windows above and below a target window."""
    if not win32gui.IsWindow(target_hwnd):
        return None, None

    blacklist_set = set(blacklist_hwnd) if blacklist_hwnd else set()
    _get_window = win32gui.GetWindow
    _gw_prev = win32con.GW_HWNDPREV
    _gw_next = win32con.GW_HWNDNEXT

    if not only_real_windows:
        above = None
        below = None

        hwnd = _get_window(target_hwnd, _gw_prev)
        while hwnd:
            if hwnd not in blacklist_set:
                above = hwnd
                break
            hwnd = _get_window(hwnd, _gw_prev)

        hwnd = _get_window(target_hwnd, _gw_next)
        while hwnd:
            if hwnd not in blacklist_set:
                below = hwnd
                break
            hwnd = _get_window(hwnd, _gw_next)

        return above, below

    else:
        _is_real = is_real_window
        above = None
        below = None

        hwnd = _get_window(target_hwnd, _gw_prev)
        while hwnd:
            if hwnd not in blacklist_set:
                try:
                    if _is_real(hwnd):
                        above = hwnd
                        break
                except Exception:
                    pass
            hwnd = _get_window(hwnd, _gw_prev)

        hwnd = _get_window(target_hwnd, _gw_next)
        while hwnd:
            if hwnd not in blacklist_set:
                try:
                    if _is_real(hwnd):
                        below = hwnd
                        break
                except Exception:
                    pass
            hwnd = _get_window(hwnd, _gw_next)

        return above, below

def get_window_above(hwnd: int, blacklist_hwnd: list[int] | None = None) -> int | None:
    """Gets the nearest window above the target window, without filter is_real_window."""
    blacklist_set = set(blacklist_hwnd) if blacklist_hwnd else set()
    h = win32gui.GetWindow(hwnd, win32con.GW_HWNDPREV)
    while h:
        if h not in blacklist_set:
            return h
        h = win32gui.GetWindow(h, win32con.GW_HWNDPREV)
    return None

def get_window_below(hwnd: int, blacklist_hwnd: list[int] | None = None) -> int | None:
    """Gets the nearest window below the target window, without filter is_real_window."""
    blacklist_set = set(blacklist_hwnd) if blacklist_hwnd else set()
    h = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
    while h:
        if h not in blacklist_set:
            return h
        h = win32gui.GetWindow(h, win32con.GW_HWNDNEXT)
    return None

def get_real_window_above(hwnd: int, blacklist_hwnd: list[int] | None = None) -> tuple[int | None, int | None]:
    """Gets the nearest visible window and the nearest above the target window."""
    blacklist_set = set(blacklist_hwnd) if blacklist_hwnd else set()
    nearest: int | None = None
    h = win32gui.GetWindow(hwnd, win32con.GW_HWNDPREV)
    while h:
        if h not in blacklist_set:
            if nearest is None:
                nearest = h
            try:
                if is_real_window(h):
                    return h, nearest
            except Exception:
                pass
        h = win32gui.GetWindow(h, win32con.GW_HWNDPREV)
    return None, nearest

def get_real_window_below(hwnd: int, blacklist_hwnd: list[int] | None = None) -> tuple[int | None, int | None]:
    """Gets the nearest visible window and the nearest below the target window."""
    blacklist_set = set(blacklist_hwnd) if blacklist_hwnd else set()
    nearest: int | None = None
    h = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
    while h:
        if h not in blacklist_set:
            if nearest is None:
                nearest = h
            try:
                if is_real_window(h):
                    return h, nearest
            except Exception:
                pass
        h = win32gui.GetWindow(h, win32con.GW_HWNDNEXT)
    return None, nearest

def get_windows_above_and_below(target_hwnd: int, only_real_windows: bool, blacklist_hwnd: list[int] | None = None) -> tuple[list[int], list[int]]:
    """Gets all windows above and below a target window in z-order."""
    blacklist_hwnd = [] if blacklist_hwnd is None else blacklist_hwnd
    above_list = []
    below_list = []
    found = False
    hwnd = win32gui.GetTopWindow(0)
    while hwnd:
        try:
            accept = (not only_real_windows) or is_real_window(hwnd)
        except Exception:
            accept = False

        if accept and (hwnd not in blacklist_hwnd or hwnd == target_hwnd):
            if hwnd == target_hwnd:
                found = True
            else:
                if not found:
                    above_list.append(hwnd)
                else:
                    below_list.append(hwnd)
        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)

    return above_list, below_list

if __name__ == "__main__":
    import math
    import timeit
    try:
        import archive.windows_layer_old as windows_layer_old
        old_functions_not_exist = False
    except ModuleNotFoundError:
        print("Failed to import module containing legacy functions")
        old_functions_not_exist = True

    hwnd_input: str = input("Enter window hwnd: ")
    if hwnd_input == "":
        hwnd: int = win32gui.GetForegroundWindow()
    elif hwnd_input.isdigit():
        hwnd = int(hwnd_input)
    else:
        hwnd = win32gui.FindWindow(None, hwnd_input)
    above, below = get_windows_above_and_below(hwnd, True)

    print(f"\nhwnd: {hwnd} ({win32gui.GetWindowText(hwnd)})")
    print(f"above ({len(above)}):", above, "-", [win32gui.GetWindowText(a) for a in above])
    print(f"below ({len(below)}):", below, "-", [win32gui.GetWindowText(a) for a in below])

    def abbreviate_number(number: float) -> str:
        if number == 0:
            return "0"
        exponent = math.floor(math.log10(abs(number)))
        precision = 3 - exponent - 1
        p = max(0, precision)
        multiplier = 10 ** p
        temp = int(number * multiplier + (1e-15 if number > 0 else -1e-15))
        result_float = temp / multiplier
        formatted = f"{result_float:.15f}"
        if '.' in formatted:
            formatted = formatted.rstrip('0').rstrip('.')
        return formatted

    def benchmark_performance(test_name, functions_list, average_samples: int = 100):
        results = []
        for function, name in functions_list:
            results.append([timeit.timeit(stmt=function, number=average_samples), name])

        results.sort(key=lambda x: x[0])
        best_time = results[0][0]

        max_name_len = max(len(w[1]) for w in results) + 2

        print(f"Test results \"{test_name}\":")
        for index, (elapsed_time, name) in enumerate(results):
            if index > 0:
                diff_previous = elapsed_time - results[index - 1][0]
                col_diff = f"difference: +{abbreviate_number(diff_previous)}s"
            else:
                col_diff = "(fastest)"

            if index > 0:
                diff_best = elapsed_time - best_time
                multiplier = elapsed_time / best_time
                col_max_diff = f"from best: +{abbreviate_number(diff_best)}s ({multiplier:.2f}x)"
            else:
                col_max_diff = ""

            col_time = f"{index + 1}. {abbreviate_number(elapsed_time)}s"
            col_name = f"- {name},"

            print(f"{col_time:<18} {col_name:<{max_name_len + 2}} {col_diff:<22} {col_max_diff}")
        print()

    print("\nTest results can vary drastically depending on active windows and computer speed")
    for only_real_windows in [True, False]:
        benchmark_performance(f"real_windows={only_real_windows}", [
            [lambda: get_immediate_neighbors_above_and_below(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v4"],
        ] + ([] if old_functions_not_exist else [
            [lambda: windows_layer_old.get_immediate_neighbors_above_and_below_v3(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v3"],
            [lambda: windows_layer_old.get_immediate_neighbors_above_and_below_v2(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v2"],
            [lambda: windows_layer_old.get_immediate_neighbors_above_and_below_v1(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v1"],
            [lambda: windows_layer_old.get_windows_above_and_below_v2(hwnd, only_real_windows), "get_windows_above_and_below_v2"],
            [lambda: windows_layer_old.get_windows_above_and_below_v1(hwnd, only_real_windows), "get_windows_above_and_below_v1"],
            [lambda: windows_layer_old.get_window_above_v1(hwnd, only_real_windows), "get_window_above_v1"],
            [lambda: (get_real_window_above(hwnd), get_real_window_below(hwnd)), "get_real_window_above+below"] if only_real_windows else [lambda: (get_window_above(hwnd), get_window_below(hwnd)), "get_window_above+below"]
        ]))

    benchmark_performance("is_real_window()", [
        [lambda: is_real_window(hwnd), "is_real_window_v3"],
    ] + ([] if old_functions_not_exist else [
        [lambda: windows_layer_old.is_real_window_v2(hwnd), "is_real_window_v2"],
        [lambda: windows_layer_old.is_real_window_v1(hwnd), "is_real_window_v1"],
    ]))

    # Test results can vary drastically depending on active windows and computer speed
    # Test results "real_windows=True":
    # 1. 0.000817s       - get_real_window_above+below (C),              (fastest)
    # 2. 0.00124s        - get_immediate_neighbors_above_and_below (C),  difference: +0.000431s from best: +0.000431s (1.53x)
    # 3. 0.00149s        - get_real_window_above+below,                  difference: +0.000247s from best: +0.000679s (1.83x)
    # 4. 0.00181s        - get_immediate_neighbors_above_and_below_v4,   difference: +0.000317s from best: +0.000996s (2.22x)
    # 5. 0.00338s        - get_immediate_neighbors_above_and_below_v3,   difference: +0.00156s  from best: +0.00256s (4.14x)
    # 6. 0.0498s         - get_immediate_neighbors_above_and_below_v2,   difference: +0.0464s   from best: +0.049s (60.96x)
    # 7. 0.099s          - get_immediate_neighbors_above_and_below_v1,   difference: +0.0492s   from best: +0.0982s (121.12x)
    # 8. 0.342s          - get_windows_above_and_below_v2,               difference: +0.243s    from best: +0.341s (418.33x)
    # 9. 0.365s          - get_windows_above_and_below_v1,               difference: +0.0237s   from best: +0.365s (447.37x)
    # 10. 0.378s         - get_window_above_v1,                          difference: +0.0122s   from best: +0.377s (462.35x)
    #
    # Test results "real_windows=False":
    # 1. 0.0000383s      - get_immediate_neighbors_above_and_below_v3,   (fastest)
    # 2. 0.0000387s      - get_immediate_neighbors_above_and_below_v2,   difference: +0.000000399s from best: +0.000000399s (1.01x)
    # 3. 0.0000396s      - get_real_window_above+below,                  difference: +0.0000009s from best: +0.00000129s (1.03x)
    # 4. 0.0000399s      - get_immediate_neighbors_above_and_below_v4,   difference: +0.0000003s from best: +0.00000159s (1.04x)
    # 5. 0.000132s       - get_immediate_neighbors_above_and_below (C),  difference: +0.0000923s from best: +0.0000939s (3.45x)
    # 6. 0.000158s       - get_real_window_above+below (C),              difference: +0.0000258s from best: +0.000119s (4.12x)
    # 7. 0.000966s       - get_immediate_neighbors_above_and_below_v1,   difference: +0.000808s from best: +0.000928s (25.18x)
    # 8. 0.00453s        - get_windows_above_and_below_v2,               difference: +0.00356s  from best: +0.00449s (118.07x)
    # 9. 0.00672s        - get_window_above_v1,                          difference: +0.00219s  from best: +0.00668s (175.18x)
    # 10. 0.355s         - get_windows_above_and_below_v1,               difference: +0.348s    from best: +0.355s (9248.38x)
    #
    # Test results "is_real_window()":
    # 1. 0.000212s       - is_real_window (C),  (fastest)
    # 2. 0.000334s       - is_real_window_v3,   difference: +0.000121s from best: +0.000121s (1.57x)
    # 3. 0.00113s        - is_real_window_v2,   difference: +0.000795s from best: +0.000917s (5.31x)
    # 4. 0.00214s        - is_real_window_v1,   difference: +0.00101s  from best: +0.00192s (10.06x)
