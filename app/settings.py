import json
from typing import TypedDict, List, Dict, Optional, cast
import copy

import app.config as config

HotkeysConfig = Dict[str, Dict[str, Optional[str]]]

WindowsLayersConfig = TypedDict("WindowsLayersConfig", {
    "title_blacklist": List[str],
    "active_blacklist": List[str],
    "class_blacklist": List[str],
})

WindowGeometryConfig = TypedDict("WindowGeometryConfig", {
    "restore": bool,
    "x": Optional[int],
    "y": Optional[int],
    "width": Optional[int],
    "height": Optional[int],
    "screen_name": Optional[str],
})

DebugConfig = TypedDict("DebugConfig", {
    "delete_logs_older_than": int,
    "active": bool,
    "hitbox_overlay": bool,
    "debug_window": bool,
    "console": bool,
})

AppConfig = TypedDict("AppConfig", {
    "FPS": int,
    "volume": int,
    "autostart": bool,
    "show_on_autostart": bool,
    "check_for_updates": bool,
    "language": str,
    "hotkeys": HotkeysConfig,
    "windows_layers": WindowsLayersConfig,
    "dashboard_refresh_ms": int,
    "window_geometry": WindowGeometryConfig,
    "debug": DebugConfig,
    "active_mods": List[str],
    "trusted_mods": List[str],
    "saved_mods_list": Dict[str, list[str]]
})

DEFAULT_SETTINGS: AppConfig = {
    "FPS": 60,
    "volume": 50,
    "autostart": False,
    "show_on_autostart": False,
    "check_for_updates": False,
    "language": "en",
    "hotkeys": {
        "app": {
            "show": None,
            "hide": None,
            "exit": None
        },
        "entities": {
            "kill all": None,
            "show all": None,
            "hide all": None,
            "kill": None,
            "show": None,
            "hide": None,
            "teleport": None
        }
    },
    "windows_layers": {
        "title_blacklist": [],
        "active_blacklist": [],
        "class_blacklist": [
            "Progman",
            "Shell_TrayWnd"
        ]
    },
    "dashboard_refresh_ms": 500,
    "window_geometry": {
        "restore": True,
        "x": None,
        "y": None,
        "width": None,
        "height": None,
        "screen_name": None
    },
    "debug": {
        "delete_logs_older_than": 3,
        "active": False,
        "hitbox_overlay": False,
        "debug_window": True,
        "console": False
    },
    "active_mods": [],
    "trusted_mods": [],
    "saved_mods_list": {}
}

def deep_fill_defaults(settings: dict, defaults: dict | None = None) -> dict:
    if defaults is None:
        defaults = DEFAULT_SETTINGS
    for key, value in defaults.items():
        if key not in settings:
            settings[key] = copy.deepcopy(value)
        elif isinstance(settings[key], dict) and isinstance(value, dict):
            deep_fill_defaults(settings[key], value)
    return settings

def load_settings() -> AppConfig:
    settings_file = config.APP_DIR / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text(encoding="utf-8"))
            return cast(AppConfig, deep_fill_defaults(settings))
        except json.JSONDecodeError:
            print("⚠️ The \"settings.json\" file is corrupt. Loading default settings.")

    settings_file.write_text(json.dumps(DEFAULT_SETTINGS, indent=4, ensure_ascii=False), encoding="utf-8")
    print("🔄 Created a local \"settings.json\" file from the defaults.")

    return cast(AppConfig, copy.deepcopy(DEFAULT_SETTINGS))
