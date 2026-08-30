from dataclasses import dataclass, field
from pathlib import Path
import json
from enum import StrEnum, auto

from PySide6.QtGui import QImageReader
from lupa import LuaRuntime

import config
import logger

log = logger.get_logger("mods_manager")
MODS_DIR = config.APP_DIR / "Mods"

class ModsAPI:
    pass

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

class ModsManager:
    def __init__(self, conn, shared_data):
        self.conn = conn
        self.shared_data = shared_data
        
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
                            entities[entity.id] = entity
        
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

        about_path = folder / "about.json"
        if not about_path.exists():
            log.warning(f"Error loading entity \"{entity_id}\" from mod \"{mod_id}\": File \"about.json\" not found")
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
                lua = LuaRuntime(unpack_returned_tuples=True)
                lua.execute("""
                    os = nil
                    io = nil
                    file = nil
                    dofile = nil
                    loadfile = nil
                    debug = nil
                    require = nil
                    package = nil
                """)

                # Sharing the program API in a mod
                lua.globals().ModsAPI = ModsAPI()

                # Running the mod code
                code = mod_lua_script_path.read_text(encoding="utf-8")
                try:
                    lua.execute(code)
                    log.info(f"Mod \"{mod_id}\" launched")
                except Exception as e:
                    log.warning(f"Error in mod code \"{mod_id}\": {e}")
            else:
                log.warning(f"Mod \"{mod_id}\" has no script")
