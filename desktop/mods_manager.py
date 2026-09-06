from dataclasses import dataclass
from pathlib import Path
import json
from enum import StrEnum, auto

import win32gui
from PySide6.QtGui import QImageReader, QColor, QPixmap
from lupa import LuaRuntime

import config
import logger
from windows_z_order.watcher import WatchWindow

log = logger.get_logger("mods_manager")
MODS_DIR = config.APP_DIR / "Mods"

class ModAPI:
    def __init__(self, entities_manager, mod_id: str) -> None:
        self._entities_manager = entities_manager
        self._mod_id: str = mod_id
        self._watch_windows: set[WatchWindow] = set()
        self._image_cache: dict[Path, QPixmap] = {}
    
    def get_foreground_window_hwnd(self) -> int:
        return win32gui.GetForegroundWindow()

    def get_window_title(self, hwnd) -> str:
        return win32gui.GetWindowText(hwnd)
    
    def watch_window(self, hwnd: int, *args: bool) -> None:
        self._watch_windows.add(WatchWindow(hwnd, *args))
    
    def stop_watching_window(self, hwnd: int, *args: bool) -> None:
        self._watch_windows.remove(WatchWindow(hwnd, *args))

    def clear_windows_watchlist(self) -> None:
        self._watch_windows.clear()

    def get_windows_watchlist(self) -> set[WatchWindow]:
        return self._watch_windows.copy()

    def get_watched_windows_info(self):
        return self._entities_manager.watcher.watched_windows.copy()

    @staticmethod
    def _normalize_color(color) -> QColor:
        if hasattr(color, "values"):
            color = QColor(*(int(x) for x in color.values()))
        else:
            color = QColor(color)
        return color

    def draw_rect(self, hwnd: int, x: int, y: int, width: int, height: int, color: str | tuple[int, int, int] | tuple[int, int, int, int]="#ff0000", filled: bool=True):
        qcolor = self._normalize_color(color)
        cmd = ("rect", x, y, width, height, qcolor, filled)
        self._entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

    def draw_line(self, hwnd: int, x1: int, y1: int, x2: int, y2: int, color: str="#ffffff", width: int=1):
        qcolor = self._normalize_color(color)
        cmd = ("line", x1, y1, x2, y2, qcolor, width)
        self._entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

    def draw_text(self, hwnd: int, x: int, y: int, text: str, color: str="#ffffff", size: int=12):
        qcolor = self._normalize_color(color)
        cmd = ("text", x, y, str(text), qcolor, size)
        self._entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

    def _resolve_mod_path(self, relative_path: str) -> Path:
        """Resolves a path a mod supplies against the mod's own folder."""
        mod_dir = (config.APP_DIR / "Mods" / self._mod_id).resolve()
        resolved = (mod_dir / relative_path).resolve()
        if not resolved.is_relative_to(mod_dir):
            raise ValueError(f'Path "{relative_path}" escapes the mod\'s own folder')
        return resolved

    def draw_image(self, hwnd: int, x: int, y: int, path: str, width: int | None = None, height: int | None = None, opacity: float = 1.0):
        """Draws an image from a file inside the mod's own folder."""
        image_path = self._resolve_mod_path(path)
        pixmap = self._image_cache.get(image_path)
        if pixmap is None:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                log.warning(f'draw_image: could not load image "{image_path}"')
                return
            self._image_cache[image_path] = pixmap
        cmd = ("image", x, y, width, height, pixmap, float(opacity))
        self._entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

    class _Logger:
        def __init__(self, mod_id: str) -> None:
            self._mod_id = mod_id
            self._log = logger.get_logger(mod_id)

        def debug(self, text: str) -> None:
            self._log.debug(text)

        def info(self, text: str) -> None:
            self._log.info(text)

        def warning(self, text: str) -> None:
            self._log.warning(text)

        def error(self, text: str) -> None:
            self._log.error(text)

        def critical(self, text: str) -> None:
            self._log.critical(text)

    @property
    def Logger(self) -> _Logger:
        return self._Logger(self._mod_id)

class ScriptLanguage(StrEnum):
    python = auto()
    lua = auto()

@dataclass
class Mod:
    id: str
    name: str
    author: str
    version: str
    description: str
    dependencies: dict[str, str]
    preview_path: Path | None
    script_language: ScriptLanguage

@dataclass
class Entity:
    id: str
    name: str
    mod_id: str
    preview_path: Path | None
    description: str = ""

def filter_attribute_access(obj, attr_name, is_setting):
    if isinstance(attr_name, str) and not attr_name.startswith("_"):
        return attr_name
    raise AttributeError("access denied")

class ModsManager:
    def __init__(self, conn, shared_data, entities_manager):
        self.conn = conn
        self.shared_data = shared_data
        self.entities_manager = entities_manager

        self.mods: list = []
        
        self.load_mods()

    def load_mods(self) -> None:
        log.info("Loading mod list...")
        mods: dict[str, Mod] = {}
        entities: dict[str, Entity] = {}
        for mod_folder_path in MODS_DIR.iterdir():
            if not mod_folder_path.is_dir():
                continue
            mod = self.load_mod_from_folder(mod_folder_path)
            if mod:
                mods[mod.id] = mod
                if mod.id in self.shared_data.settings["active_mods"]:
                    for entity_path in (mod_folder_path / "entities").iterdir():
                        entity = self.load_entity_from_folder(entity_path, mod.id)
                        if entity:
                            entities[f"{mod.id}:{entity.id}"] = entity

        self.shared_data.mods = mods
        self.shared_data.entities = entities
        log.info(f"Mods loaded: {len(mods)}")
        log.info(f"Entities loaded: {len(entities)}")
        self.conn.send(["Update mod list"])

    def load_mod_from_folder(self, folder: Path) -> Mod | None:
        mod_id = folder.name
        
        about_path = folder / "about.json"
        if not about_path.exists():
            log.warning(f"Error loading mod \"{mod_id}\": File \"about.json\" not found")
            return None
        about_data = json.loads(about_path.read_text(encoding="utf-8"))
    
        supported_image_formats = {
            bytes(fmt.data()).decode("utf-8").lower()
            for fmt in QImageReader.supportedImageFormats()
        }
        for extension in supported_image_formats:
            preview_file_path = (folder / "preview").with_suffix(f".{extension}")
            if preview_file_path.exists():
                break
        else:
            log.warning(f"Error loading mod \"{mod_id}\": Preview image not found")
            preview_file_path = None

        if (folder / "main.py").exists():
            script_language = ScriptLanguage.python
        elif (folder / "main.lua").exists():
            script_language = ScriptLanguage.lua
        else:
            log.warning(f"Error loading mod \"{mod_id}\": main script missing")
            return None
    
        return Mod(
            id=mod_id,
            name=about_data.get("name", mod_id),
            author=about_data.get("author", "unknown"),
            version=about_data.get("version", "0.0.0"),
            description=about_data.get("description", "No description available."),
            dependencies=about_data.get("dependencies", {}),
            preview_path=preview_file_path,
            script_language=script_language
        )

    def load_entity_from_folder(self, folder: Path, mod_id: str) -> Entity | None:
        entity_id = folder.name
        mod_id = mod_id

        about_path = folder / "about_entity.json"
        if not about_path.exists():
            log.warning(f"Error loading entity \"{entity_id}\" from mod \"{mod_id}\": File \"about_entity.json\" not found")
            return None
        about_data = json.loads(about_path.read_text(encoding="utf-8"))

        supported_image_formats = {
            bytes(fmt.data()).decode("utf-8").lower()
            for fmt in QImageReader.supportedImageFormats()
        }
        for extension in supported_image_formats:
            preview_file_path = (folder / "preview").with_suffix(f".{extension}")
            if preview_file_path.exists():
                break
        else:
            log.warning(f"Error loading entity \"{entity_id}\" from mod \"{mod_id}\": Preview image not found")
            preview_file_path = None

        return Entity(
            id=entity_id,
            name=about_data.get("name", entity_id),
            mod_id=mod_id,
            preview_path=preview_file_path,
            description=about_data.get("description", "No description available."),
        )

    def run_mods(self):
        settings = self.shared_data.settings
        settings["active_mods"] = [mod_id for mod_id in settings["active_mods"] if mod_id in self.shared_data.mods]
        self.shared_data.settings = settings
        with open(config.APP_DIR / "settings.json", "w", encoding="utf-8") as f:
            json.dump(self.shared_data.settings, f, indent=4, ensure_ascii=False)
        
        for mod_id in self.shared_data.settings["active_mods"]:
            mod_python_script_path = MODS_DIR / mod_id / "main.py"
            mod_lua_script_path = MODS_DIR / mod_id / "main.lua"

            if mod_python_script_path.exists():
                pass # TODO: Dodaj obsługę modów napisanych w python
            elif mod_lua_script_path.exists():
                lua = LuaRuntime(
                    unpack_returned_tuples=True,
                    register_eval=False,
                    register_builtins=False,
                    attribute_filter=filter_attribute_access,
                )

                lua.execute("""
                    os = nil
                    io = nil
                    file = nil
                    dofile = nil
                    loadfile = nil
                    debug = nil
                    require = nil
                    package = nil
                    load = nil
                    python = nil
                """)

                # Sharing the program API in a mod
                lua.globals().ModAPI = ModAPI(self.entities_manager, mod_id)

                # Running the mod code
                code = mod_lua_script_path.read_text(encoding="utf-8")
                try:
                    lua.execute(code)
                    self.mods.append(lua)
                    log.info(f"Mod \"{mod_id}\" launched")
                except Exception as e:
                    log.warning(f"Error in mod code \"{mod_id}\": {e}")
            else:
                log.warning(f"Mod \"{mod_id}\" has no script")
