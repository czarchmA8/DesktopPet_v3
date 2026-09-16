"""file created only for automatic code completion in application"""
from multiprocessing.managers import SyncManager
from argparse import Namespace
from desktop.mods_manager import Mod, Entity

class SharedState:
    args: Namespace
    """Stores application startup arguments"""

    settings: dict
    """Stores settings from `settings.json`"""

    restarted: bool
    """Stores information whether the application has already been restarted"""

    active_mods: dict[str, Mod]
    """Stores information about mods such as name, author, description, etc."""

    spawnable_entities: dict[str, Entity]
    """Stores information about entities such as name, mod id, description, etc."""

    displayed_entities: dict[str, str]
    """Stores all unique entity IDs along with the entity ID."""

    restart_requested: bool
    """stores information about whether the application should be restarted instead of closed"""

    selected_entity: str | None
    """Stores the unique ID of the selected entity"""

    entity_details: dict[str, str]
    """Stores additional information about the selected entity retrieved via the mod's API"""

    def __init__(self, manager: SyncManager) -> None: ...
    def pull(self) -> None: ...
