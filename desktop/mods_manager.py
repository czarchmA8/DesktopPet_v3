from dataclasses import dataclass
from pathlib import Path
import json
from enum import StrEnum, Enum, auto
from typing import Callable
import uuid

import win32gui
from PySide6.QtGui import QImageReader, QColor, QPixmap, QImage, QCursor
from lupa.lua54 import LuaRuntime

import config
import logger
from shared_state import SharedState
from windows_z_order.watcher import WatchWindow

log = logger.get_logger("mods_manager")
MODS_DIR = config.APP_DIR / "Mods"

class InputState(Enum):
    pressed = auto()
    holding = auto()
    released = auto()

class MouseButtonName(StrEnum):
    left = "LeftButton"
    middle = "MiddleButton"
    right = "RightButton"
    forward = "ForwardButton"
    back = "BackButton"

@dataclass
class MouseButtonEvent:
    state: InputState
    x: int
    y: int
    pressed_at: float
    released_at: float | None = None
    hit_id: str | None = None

@dataclass
class MouseScroll:
    x: int = 0
    y: int = 0
    hit_id: str | None = None

class ModAPI:
    def __init__(self, mods_manager: "ModsManager", mod_id: str) -> None:
        self._mods_manager = mods_manager
        self._mod_id: str = mod_id
        self._watch_windows: set[WatchWindow] = set()
        self._image_cache: dict[Path, tuple[QPixmap, QImage]] = {}

        self.Logger = self._Logger(self._mod_id)
        self.Mouse = self._Mouse(self._mods_manager)
    
    def _print(self, *args, sep: str=" ") -> None:
        self.Logger.debug(sep.join(args))
    
    def register_entity(self, entity_id: str, name: str, preview_path: str | None, description: str | None, create_func) -> None:
        key = f"{self._mod_id}:{entity_id}"
        self._mods_manager.spawnable_entities[f"{self._mod_id}:{entity_id}"] = Entity(
            id=entity_id,
            name=name,
            mod_id=self._mod_id,
            preview_path=(config.APP_DIR / "Mods" / self._mod_id / preview_path) if preview_path else None,
            description=description if description else "No description available."
        )
        self._mods_manager.entity_factories[key] = create_func
        self._mods_manager.spawnable_entities_dirty = True
    
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
        return self._mods_manager.entities_manager.watcher.watched_windows.copy()

    @staticmethod
    def _normalize_color(color) -> QColor:
        if hasattr(color, "values"):
            color = QColor(*(int(x) for x in color.values()))
        else:
            color = QColor(color)
        return color

    def draw_rect(self, hwnd: int, x: int, y: int, width: int, height: int, color: str | tuple[int, int, int] | tuple[int, int, int, int]="#ff0000", filled: bool=True, hit_id: str | None = None):
        qcolor = self._normalize_color(color)
        cmd = ("rect", x, y, width, height, qcolor, filled, hit_id)
        self._mods_manager.entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

    def draw_line(self, hwnd: int, x1: int, y1: int, x2: int, y2: int, color: str="#ffffff", width: int=1, hit_id: str | None = None):
        qcolor = self._normalize_color(color)
        cmd = ("line", x1, y1, x2, y2, qcolor, width, hit_id)
        self._mods_manager.entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

    def draw_text(self, hwnd: int, x: int, y: int, text: str, color: str="#ffffff", size: int=12):
        qcolor = self._normalize_color(color)
        cmd = ("text", x, y, str(text), qcolor, size)
        self._mods_manager.entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

    def _resolve_mod_path(self, relative_path: str) -> Path:
        """Resolves a path a mod supplies against the mod's own folder."""
        mod_dir = (config.APP_DIR / "Mods" / self._mod_id).resolve()
        resolved = (mod_dir / relative_path).resolve()
        if not resolved.is_relative_to(mod_dir):
            raise ValueError(f'Path "{relative_path}" escapes the mod\'s own folder')
        return resolved

    def draw_image(self, hwnd: int, x: int, y: int, path: str, width: int | None = None, height: int | None = None, opacity: float = 1.0, hit_id: str | None = None):
        """Draws an image from a file inside the mod's own folder."""
        opacity = 1.0 if opacity is None else float(opacity)
        
        image_path = self._resolve_mod_path(path)
        cached = self._image_cache.get(image_path)
        if cached is None:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                log.warning(f'draw_image: could not load image "{image_path}"')
                return
            alpha_image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
            cached = (pixmap, alpha_image)
            self._image_cache[image_path] = cached

        pixmap, alpha_image = cached
        cmd = ("image", x, y, width, height, pixmap, opacity, alpha_image, hit_id)
        self._mods_manager.entities_manager.transparent_windows[hwnd].draw_commands.append(cmd)

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
    
    class _Mouse:
        def __init__(self, mods_manager: "ModsManager"):
            self._mods_manager = mods_manager

        def _get_button_name(self, button: str):
            for element in MouseButtonName:
                if button.lower() == element.name:
                    button = element.value
                    break
            return button

        def get_button_event(self, button: str) -> MouseButtonEvent | None:
            return self._mods_manager.mouse_events.get(button, None)

        def is_entity_clicked(self, hit_id: str) -> bool:
            event = self.get_button_event(MouseButtonName.left)
            if event:
                return event.state == InputState.pressed and event.hit_id == hit_id
            else:
                return False

        def is_entity_pressed(self, button: str, hit_id: str) -> bool:
            button = self._get_button_name(button)
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.pressed and event.hit_id == hit_id
            else:
                return False

        def is_entity_holding(self, button: str, hit_id: str) -> bool:
            button = self._get_button_name(button)
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.holding and event.hit_id == hit_id
            else:
                return False

        def is_entity_released(self, button: str, hit_id: str) -> bool:
            button = self._get_button_name(button)
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.released and event.hit_id == hit_id
            else:
                return False

        def get_pos(self) -> tuple[int, int]:
            pos = QCursor.pos()
            return pos.x(), pos.y()

        def get_scroll(self) -> MouseScroll:
            return self._mods_manager.mouse_scroll

        def get_entity_scroll(self, hit_id: str) -> int:
            if self._mods_manager.mouse_scroll.hit_id == hit_id:
                return self._mods_manager.mouse_scroll.y
            else:
                return 0

        def get_entity_scroll_x(self, hit_id: str) -> int:
            if self._mods_manager.mouse_scroll.hit_id == hit_id:
                return self._mods_manager.mouse_scroll.x
            else:
                return 0

    def is_focused(self, instance_id: str) -> bool:
        return NotImplemented # TODO: Dodaj funkcję zwracającą czy dane entity jest wybrane

    def kill_entity(self, instance_id: str) -> None:
        self._mods_manager.kill_entity(instance_id)

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
    """Entity metadata goes to shared_data (dashboard reads it)."""
    id: str
    name: str
    mod_id: str
    preview_path: Path | None
    description: str

@dataclass
class EntityData:
    """Functions of a specific spawned instance"""
    delete_func: Callable
    show_func: Callable
    hide_func: Callable
    teleport_func: Callable
    get_info_func: Callable
    tick_func: Callable
    paint_tick_func: Callable

def filter_attribute_access(obj, attr_name, is_setting):
    if isinstance(attr_name, str) and not attr_name.startswith("_"):
        return attr_name
    raise AttributeError("access denied")

class ModsManager:
    def __init__(self, conn, shared_data: SharedState, entities_manager):
        self.conn = conn
        self.shared_data: SharedState = shared_data
        self.entities_manager = entities_manager

        self.displayed_entities: dict[str, EntityData] = {}
        self.entity_factories: dict[str, Callable] = {}
        self.spawnable_entities: dict[str, Entity] = {}
        self.spawnable_entities_dirty: bool = False

        self.mouse_events: dict[str, MouseButtonEvent] = {}
        self.mouse_scroll: MouseScroll = MouseScroll()

        self.mod_runtimes: list[LuaRuntime] = []
        
        self.load_mods()

    def load_mods(self) -> None:
        log.info("Loading mod list...")
        active_mods: dict[str, Mod] = {}
        for mod_folder_path in MODS_DIR.iterdir():
            if not mod_folder_path.is_dir():
                continue
            mod = self.load_mod_from_folder(mod_folder_path)
            if mod:
                active_mods[mod.id] = mod

        self.shared_data.active_mods = active_mods
        log.info(f"Mods loaded: {len(active_mods)}")
        self.send_ipc_command(["Update_mod_list"])
    
    def send_ipc_command(self, msg: list[str]):
        """Sends message to other processes"""
        log.debug(f"Sent IPC: {msg}")
        self.conn.send(msg)

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

    def run_mods(self) -> None:
        settings = self.shared_data.settings
        settings["active_mods"] = [mod_id for mod_id in settings["active_mods"] if mod_id in self.shared_data.active_mods]
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
                mod_api = ModAPI(self, mod_id)
                lua.globals().ModAPI = mod_api
                lua.globals().print = mod_api._print

                # Running the mod code
                code = mod_lua_script_path.read_text(encoding="utf-8")
                try:
                    lua.execute(code)
                    self.mod_runtimes.append(lua)
                    log.info(f"Mod \"{mod_id}\" launched")
                except Exception as e:
                    log.warning(f"Error in mod code \"{mod_id}\": {e}")
            else:
                log.warning(f"Mod \"{mod_id}\" has no script")
    
    def tick(self) -> set[WatchWindow]:
        # global mod tick
        watch_windows: set[WatchWindow] = set()
        for mod in self.mod_runtimes:
            mod.globals().ModAPI._watch_windows.clear()
            if "tick" in mod.globals():
                mod.globals().tick()

        # instances (entities) tick
        for entity_data in self.displayed_entities.values():
            if entity_data.tick_func:
                entity_data.tick_func()

        for mod in self.mod_runtimes:
            watch_windows.update(mod.globals().ModAPI._watch_windows)

        # Updating the mouse button state: pressed -> holding and released -> remove
        for button, event in dict(self.mouse_events).items():
            if event.state == InputState.pressed:
                self.mouse_events[button].state = InputState.holding
            elif event.state == InputState.holding:
                pos = QCursor.pos()
                self.mouse_events[button].x = pos.x()
                self.mouse_events[button].y = pos.y()
            elif event.state == InputState.released:
                self.mouse_events.pop(button)
        self.mouse_scroll = MouseScroll() # Restarting mouse scroll changes

        # updating the list of entities in the dashboard
        if self.spawnable_entities_dirty:
            self.spawnable_entities_dirty = False
            self.entities_manager.shared_data.spawnable_entities = self.spawnable_entities
            self.entities_manager.send_ipc_command(["Update_spawnable_entities_list"])
        
        return watch_windows
    
    def paint_tick(self) -> None:
        for mod in self.mod_runtimes:
            if "paint_tick" in mod.globals():
                mod.globals().paint_tick()

        for entity_data in self.displayed_entities.values():
            if entity_data.paint_tick_func:
                entity_data.paint_tick_func()

    def spawn_entity(self, mod_id: str, entity_id: str) -> str | None:
        key = f"{mod_id}:{entity_id}"
        create_func = self.entity_factories.get(key)
        if create_func is None:
            log.warning(f'Entity "{key}" not found')
            return None

        instance_id = str(uuid.uuid4())
        funcs = create_func(instance_id)
        self.displayed_entities[instance_id] = EntityData(
            delete_func=funcs["delete_func"],
            show_func=funcs["show_func"],
            hide_func=funcs["hide_func"],
            teleport_func=funcs["teleport_func"],
            get_info_func=funcs["get_info_func"],
            tick_func=funcs["tick_func"],
            paint_tick_func=funcs["paint_tick_func"],
        )

        displayed = self.entities_manager.shared_data.displayed_entities
        displayed[instance_id] = key
        self.entities_manager.shared_data.displayed_entities = displayed
        self.entities_manager.send_ipc_command(["Update_displayed_entities"])

        return instance_id

    def kill_entity(self, instance_id: str) -> None:
        entity_data = self.displayed_entities.pop(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.delete_func()

        displayed = dict(self.entities_manager.shared_data.displayed_entities)
        displayed.pop(instance_id, None)
        self.entities_manager.shared_data.displayed_entities = displayed
        self.entities_manager.send_ipc_command(["Update_displayed_entities"])
    
    def show_entity(self, instance_id: str) -> None:
        entity_data = self.displayed_entities.get(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.show_func()
    
    def hide_entity(self, instance_id: str) -> None:
        entity_data = self.displayed_entities.get(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.hide_func()
    
    def teleport_entity(self, instance_id: str) -> None:
        entity_data = self.displayed_entities.get(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.teleport_func()
    
    def kill_all_entities(self):
        for entity_data in self.displayed_entities.values():
            entity_data.delete_func()
        self.displayed_entities.clear()
        self.entities_manager.shared_data.displayed_entities = {}
        self.entities_manager.send_ipc_command(["Update_displayed_entities"])
    
    def show_all_entities(self):
        for entity_data in self.displayed_entities.values():
            entity_data.show_func()
    
    def hide_all_entities(self):
        for entity_data in self.displayed_entities.values():
            entity_data.hide_func()
