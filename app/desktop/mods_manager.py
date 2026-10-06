from dataclasses import dataclass, fields
from pathlib import Path
import json
from enum import StrEnum, auto
from typing import Callable
import uuid
import importlib.util
import sys
from types import ModuleType
import time

from PySide6.QtGui import QImageReader, QCursor
from lupa.lua54 import LuaRuntime

import app.config as config
import app.logger as logger
from app.shared_state import SharedState
from app.desktop.input_events import InputState, MouseButtonEvent, MouseScroll

log = logger.get_logger("mods_manager")
MODS_DIR = config.APP_DIR / "Mods"

class ScriptLanguage(StrEnum):
    """Language of a mod script."""
    python = auto()
    lua = auto()

@dataclass(frozen=True)
class Mod:
    """Metadata of the running mod (`ModAPI.Mod`), read from its `about.json` and its folder."""
    id: str
    """Name of the mod folder."""
    name: str
    """`name` from `about.json`, the mod ID if missing."""
    author: str
    """`author` from `about.json`, `unknown` if missing."""
    version: str
    """`version` from `about.json`, `0.0.0` if missing."""
    description: str
    """`description` from `about.json`."""
    dependencies: dict[str, str]
    """`dependencies` from `about.json`; stored, but not enforced by the loader."""
    preview_path: str | None
    """Path of the preview image in the mod folder, or None.."""
    script_language: ScriptLanguage
    """Language of the mod script."""

@dataclass
class ModInstance:
    """A running mod."""
    id: str
    script_language: ScriptLanguage
    runtime: LuaRuntime | ModuleType

@dataclass(frozen=True)
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

@dataclass(frozen=True)
class EntityCallbacks:
    """Functions of a specific spawned instance"""
    delete_func: Callable
    show_func: Callable
    hide_func: Callable
    teleport_func: Callable
    get_info_func: Callable
    tick_func: Callable

def filter_attribute_access(obj, attr_name, is_setting):
    """Attribute filter of the Lua runtime"""
    if isinstance(attr_name, str) and not attr_name.startswith("_"):
        return attr_name
    raise AttributeError("access denied")

class ModsManager:
    """Loads mods, runs their scripts and updates the spawned entities every frame."""

    def __init__(self, conn, shared_data: SharedState, overlay_manager):
        from app.desktop.overlay_manager import OverlayManager

        self.conn = conn
        self.shared_data: SharedState = shared_data
        self.overlay_manager: OverlayManager = overlay_manager

        self.displayed_entities: dict[str, EntityCallbacks] = {}
        self.entity_factories: dict[str, Callable] = {}
        self.spawnable_entities: dict[str, Entity] = {}
        self.spawnable_entities_dirty: bool = False

        self.mouse_events: dict[str, MouseButtonEvent] = {}
        self.mouse_scroll: MouseScroll = MouseScroll()

        self.last_tick_time = 0.0

        self.loaded_mods: list[ModInstance] = []
        
        self.load_mods()

    def load_mods(self) -> None:
        """Scans `Mods/` and publishes the valid mods to the shared state."""
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
        """Loads information about the mod. Returns None if the mod is invalid."""
        mod_id = folder.name
        
        about_path = folder / "about.json"
        if not about_path.exists():
            log.warning(f"Error loading mod \"{mod_id}\": File \"about.json\" not found")
            return None
        try:
            about_data = json.loads(about_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            log.warning(f"Error loading mod \"{mod_id}\": cannot read \"about.json\": {e}")
            return None
        if not isinstance(about_data, dict):
            log.warning(f"Error loading mod \"{mod_id}\": \"about.json\" must contain a JSON object")
            return None
    
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
            preview_path=preview_file_path.resolve().as_posix() if preview_file_path is not None else None,
            script_language=script_language
        )

    def _run_python_mod(self, mod_id: str, script_path: Path) -> None:
        from app.desktop.mod_api import ModAPI

        module_name = f"mod_{mod_id}"
        spec = importlib.util.spec_from_file_location(module_name, script_path)
        if spec is None or spec.loader is None:
            log.warning(f'Error loading mod "{mod_id}": cannot create module spec')
            return

        module = importlib.util.module_from_spec(spec)
        mod_api = ModAPI(self, mod_id)
        module.__dict__.update(ModAPI=mod_api, print=mod_api._print)

        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            sys.modules.pop(module_name, None)
            log.warning(f'Error in mod code "{mod_id}": {e}')
            return

        self.loaded_mods.append(ModInstance(mod_id, ScriptLanguage.python, module))
        log.info(f'Mod "{mod_id}" launched')
    
    def _run_lua_mod(self, mod_id: str, script_path: Path) -> None:
        from app.desktop.mod_api import ModAPI

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
        code = script_path.read_text(encoding="utf-8")
        try:
            lua.execute(code)
            self.loaded_mods.append(ModInstance(mod_id, ScriptLanguage.lua, lua))
            log.info(f"Mod \"{mod_id}\" launched")
        except Exception as e:
            log.warning(f"Error in mod code \"{mod_id}\": {e}")
    
    def run_mods(self) -> None:
        """Runs enabled mods."""
        settings = self.shared_data.settings
        settings["active_mods"] = [mod_id for mod_id in settings["active_mods"] if mod_id in self.shared_data.active_mods]
        self.shared_data.settings = settings
        with open(config.APP_DIR / "settings.json", "w", encoding="utf-8") as f:
            json.dump(self.shared_data.settings, f, indent=4, ensure_ascii=False)
        
        for mod_id in self.shared_data.settings["active_mods"]:
            mod_python_script_path = MODS_DIR / mod_id / "main.py"
            mod_lua_script_path = MODS_DIR / mod_id / "main.lua"

            if mod_python_script_path.exists():
                self._run_python_mod(mod_id, mod_python_script_path)
            elif mod_lua_script_path.exists():
                self._run_lua_mod(mod_id, mod_lua_script_path)
            else:
                log.warning(f"Mod \"{mod_id}\" has no script")
    
    def tick(self) -> None:
        current_time = time.perf_counter()
        if self.last_tick_time == 0.0:
            self.last_tick_time = current_time
        dt = current_time - self.last_tick_time
        self.last_tick_time = current_time

        hitbox_overlay = self.shared_data.settings["debug"]["active"] and self.shared_data.settings["debug"]["hitbox_overlay"]
        # global mod tick
        for mod in self.loaded_mods:
            if mod.script_language == ScriptLanguage.python:
                tick_func = getattr(mod.runtime, "tick", None)
                if tick_func is not None:
                    tick_func(dt, hitbox_overlay)
            elif mod.script_language == ScriptLanguage.lua:
                if "tick" in mod.runtime.globals():
                    mod.runtime.globals().tick(dt, hitbox_overlay)
            else:
                raise Exception("Unknown script language")

        # instances (entities) tick
        for entity_data in list(self.displayed_entities.values()):
            entity_data.tick_func(dt, hitbox_overlay)

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
        """Creates an instance of a registered entity and returns its ID, or None on failure."""
        key = f"{mod_id}:{entity_id}"
        create_func = self.entity_factories.get(key)
        if create_func is None:
            log.warning(f'Entity "{key}" not found')
            return None

        instance_id = str(uuid.uuid4())
        entity_funcs: dict[str, Callable] = create_func(instance_id)
        try:
            self.displayed_entities[instance_id] = EntityCallbacks(**{
                field.name: entity_funcs[field.name] if field.name in entity_funcs else _noop
                for field in fields(EntityCallbacks)
            })
        except TypeError as e:
            log.error(
                f'Error {e}. \n'
                'The "create_func" function must return a dictionary containing any of these functions: \n'
                f'{[field.name for field in fields(EntityCallbacks)]}'
            )
            return None

        displayed = self.overlay_manager.shared_data.displayed_entities
        displayed[instance_id] = key
        self.overlay_manager.shared_data.displayed_entities = displayed
        self.overlay_manager.send_ipc_command(["Update_displayed_entities"])

        return instance_id

    def kill_entity(self, instance_id: str) -> None:
        """Removes an instance and calls its `delete_func`."""
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
        """Calls the `show_func` of an instance."""
        entity_data = self.displayed_entities.get(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.show_func()
    
    def hide_entity(self, instance_id: str) -> None:
        """Calls the `hide_func` of an instance."""
        entity_data = self.displayed_entities.get(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.hide_func()
    
    def teleport_entity(self, instance_id: str) -> None:
        """Calls the `teleport_func` of an instance."""
        entity_data = self.displayed_entities.get(instance_id, None)
        if entity_data is None:
            log.warning(f'Instance "{instance_id}" not found')
            return
        entity_data.teleport_func()
    
    def kill_all_entities(self):
        """Removes all instances, calling their `delete_func`."""
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
