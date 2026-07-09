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
# Module-level DWM handle – loaded once at import
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
    '''Gets the nearest visible windows above and below a target window'''
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

def get_windows_above_and_below(target_hwnd: int, only_real_windows: bool, blacklist_hwnd: list[int] | None = None) -> tuple[list[int], list[int]]:
    '''Gets all windows above and below a target window in z-order'''
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

    def benchmark_performance(test_name, functions_list, average_samples: int = 30):
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
            [lambda: get_immediate_neighbors_above_and_below(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v4"]
        ] + [] if old_functions_not_exist else [
            [lambda: windows_layer_old.get_immediate_neighbors_above_and_below_v3(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v3"],
            [lambda: windows_layer_old.get_immediate_neighbors_above_and_below_v2(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v2"],
            [lambda: windows_layer_old.get_immediate_neighbors_above_and_below_v1(hwnd, only_real_windows), "get_immediate_neighbors_above_and_below_v1"],
            [lambda: windows_layer_old.get_windows_above_and_below_v2(hwnd, only_real_windows), "get_windows_above_and_below_v2"],
            [lambda: windows_layer_old.get_windows_above_and_below_v1(hwnd, only_real_windows), "get_windows_above_and_below_v1"],
            [lambda: windows_layer_old.get_window_above_v1(hwnd, only_real_windows), "get_window_above_v1"]
        ])

    benchmark_performance("is_real_window()", [
        [lambda: is_real_window(hwnd), "is_real_window_v3"]
    ] + [] if old_functions_not_exist else [
        [lambda: windows_layer_old.is_real_window_v2(hwnd), "is_real_window_v2"],
        [lambda: windows_layer_old.is_real_window_v1(hwnd), "is_real_window_v1"],
    ])

    # Wyniki tekstów mogą drastycznie się zmienić w zależności od aktywnych okien i prędkości komputera
    # Wyniki testu "real_windows=True":
    # 1. 0.000285s       - get_immediate_neighbors_above_and_below_v4,  (najszybszy)
    # 2. 0.000816s       - get_immediate_neighbors_above_and_below_v3,  różnica: +0.00053s     od najlepszego: +0.00053s (2.86x)
    # 3. 0.00612s        - get_immediate_neighbors_above_and_below_v2,  różnica: +0.0053s      od najlepszego: +0.00583s (21.45x)
    # 4. 0.0184s         - get_immediate_neighbors_above_and_below_v1,  różnica: +0.0123s      od najlepszego: +0.0182s (64.75x)
    # 5. 0.096s          - get_windows_above_and_below_v2,              różnica: +0.0775s      od najlepszego: +0.0957s (336.36x)
    # 6. 0.0967s         - get_window_above_v1,                         różnica: +0.000707s    od najlepszego: +0.0964s (338.84x)
    # 7. 0.101s          - get_windows_above_and_below_v1,              różnica: +0.00503s     od najlepszego: +0.101s (356.48x)
    #
    # Wyniki testu "real_windows=False":
    # 1. 0.0000129s      - get_immediate_neighbors_above_and_below_v3,  (najszybszy)
    # 2. 0.0000131s      - get_immediate_neighbors_above_and_below_v2,  różnica: +0.000000199s od najlepszego: +0.000000199s (1.02x)
    # 3. 0.0000153s      - get_immediate_neighbors_above_and_below_v4,  różnica: +0.0000021s   od najlepszego: +0.0000023s (1.18x)
    # 4. 0.000219s       - get_immediate_neighbors_above_and_below_v1,  różnica: +0.000204s    od najlepszego: +0.000206s (16.88x)
    # 5. 0.00119s        - get_windows_above_and_below_v2,              różnica: +0.00097s     od najlepszego: +0.00117s (91.55x)
    # 6. 0.00196s        - get_window_above_v1,                         różnica: +0.000778s    od najlepszego: +0.00195s (151.41x)
    # 7. 0.0988s         - get_windows_above_and_below_v1,              różnica: +0.0969s      od najlepszego: +0.0988s (7607.62x)
    #
    # Wyniki testu "is_real_window()":
    # 1. 0.000103s       - is_real_window_v3,  (najszybszy)
    # 2. 0.000535s       - is_real_window_v2,  różnica: +0.000432s    od najlepszego: +0.000432s (5.19x)
    # 3. 0.000662s       - is_real_window_v1,  różnica: +0.000127s    od najlepszego: +0.000559s (6.43x)
