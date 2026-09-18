from dataclasses import dataclass
from pathlib import Path
import json
from enum import StrEnum, auto
from typing import Callable
import uuid

from PySide6.QtGui import QImageReader, QCursor
from lupa.lua54 import LuaRuntime

import config
import logger
from shared_state import SharedState
from desktop.input_events import InputState, MouseButtonEvent, MouseScroll

log = logger.get_logger("mods_manager")
MODS_DIR = config.APP_DIR / "Mods"

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

def _noop(*args, **kwargs) -> None:
    """An empty function that does nothing."""
    pass

@dataclass
class EntityData:
    """Functions of a specific spawned instance"""
    delete_func: Callable
    show_func: Callable
    hide_func: Callable
    teleport_func: Callable
    get_info_func: Callable
    tick_func: Callable

def filter_attribute_access(obj, attr_name, is_setting):
    if isinstance(attr_name, str) and not attr_name.startswith("_"):
        return attr_name
    raise AttributeError("access denied")

class ModsManager:
    def __init__(self, conn, shared_data: SharedState, overlay_manager):
        self.conn = conn
        self.shared_data: SharedState = shared_data
        self.overlay_manager = overlay_manager

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
        from desktop.mod_api import ModAPI

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
    
    def tick(self) -> None:
        hitbox_overlay = self.shared_data.settings["debug"]["active"] and self.shared_data.settings["debug"]["hitbox_overlay"]
        # global mod tick
        for mod in self.mod_runtimes:
            if "tick" in mod.globals():
                mod.globals().tick(hitbox_overlay)

        # instances (entities) tick
        for entity_data in self.displayed_entities.values():
            entity_data.tick_func(hitbox_overlay)

        # Retrieving detailed information about the selected entity
        selected = self.shared_data.selected_entity
        entity = self.displayed_entities.get(selected, None) if selected is not None else None
        if entity is not None:
            data = entity.get_info_func()
            if data is not None:
                self.shared_data.entity_details = dict(data)
            else:
                self.shared_data.entity_details = {}
        else:
            self.shared_data.entity_details = {}

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
            self.overlay_manager.shared_data.spawnable_entities = self.spawnable_entities
            self.overlay_manager.send_ipc_command(["Update_spawnable_entities_list"])

    def spawn_entity(self, mod_id: str, entity_id: str) -> str | None:
        key = f"{mod_id}:{entity_id}"
        create_func = self.entity_factories.get(key)
        if create_func is None:
            log.warning(f'Entity "{key}" not found')
            return None

        instance_id = str(uuid.uuid4())
        funcs = create_func(instance_id)
        self.displayed_entities[instance_id] = EntityData(
            delete_func=funcs["delete_func"] if "delete_func" in funcs else _noop,
            show_func=funcs["show_func"] if "show_func" in funcs else _noop,
            hide_func=funcs["hide_func"] if "hide_func" in funcs else _noop,
            teleport_func=funcs["teleport_func"] if "teleport_func" in funcs else _noop,
            get_info_func=funcs["get_info_func"] if "get_info_func" in funcs else _noop,
            tick_func=funcs["tick_func"] if "tick_func" in funcs else _noop,
        )

        displayed = self.overlay_manager.shared_data.displayed_entities
        displayed[instance_id] = key
        self.overlay_manager.shared_data.displayed_entities = displayed
        self.overlay_manager.send_ipc_command(["Update_displayed_entities"])

        return instance_id

    def kill_entity(self, instance_id: str) -> None:
        entity_data = self.displayed_entities.pop(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.delete_func()

        displayed = dict(self.overlay_manager.shared_data.displayed_entities)
        displayed.pop(instance_id, None)
        self.overlay_manager.shared_data.displayed_entities = displayed
        self.overlay_manager.send_ipc_command(["Update_displayed_entities"])
    
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
        self.overlay_manager.shared_data.displayed_entities = {}
        self.overlay_manager.send_ipc_command(["Update_displayed_entities"])
    
    def show_all_entities(self):
        for entity_data in self.displayed_entities.values():
            entity_data.show_func()
    
    def hide_all_entities(self):
        for entity_data in self.displayed_entities.values():
            entity_data.hide_func()
    
    def select_entity(self, instance_id: str) -> None:
        self.shared_data.selected_entity = instance_id
        if self.shared_data.selected_entity in self.shared_data.displayed_entities:
            self.send_ipc_command(["select_entity", instance_id])
