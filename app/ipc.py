from multiprocessing.managers import SyncManager
from multiprocessing.connection import PipeConnection
import logging
from typing import Iterator

class IpcChannel:
    def __init__(self, conn: PipeConnection, tag: str, peer: str, log: logging.Logger) -> None:
        self._conn = conn
        self.tag = tag
        self.peer = peer
        self._log = log
        self._broken = False

    def send(self, msg: list) -> bool:
        try:
            self._conn.send(msg)
        except OSError as e:
            self._log_broken(f"Failed to send to {self.peer}: {msg} ({e!r})")
            return False
        self._log.debug(f"[{self.tag}] Sent to {self.peer}: {msg}")
        return True

    def receive(self) -> Iterator[list]:
        while True:
            try:
                if not self._conn.poll():
                    return
                msg = self._conn.recv()
            except (EOFError, OSError) as e:
                self._log_broken(f"Failed to receive from {self.peer}: {e!r}")
                return
            self._log.debug(f"[{self.tag}] Received from {self.peer}: {msg}")
            yield msg

    def unknown(self, msg: list) -> None:
        self._log.error(f"[{self.tag}] Unknown command from {self.peer}: {msg}")

    def _log_broken(self, text: str) -> None:
        if not self._broken:
            self._log.error(f"[{self.tag}] {text}")
            self._broken = True

class SharedState:
    """
    Local interface for accessing and modifying data shared between processes.

    The class keeps a local cache of shared values. Calling ``pull()`` marks
    all currently shared values as dirty. A dirty value is fetched from the
    shared ``Manager`` dictionary on its next access.

    Example:
        # Refresh all shared values.
        shared.pull()

        # Read values.
        print(shared.restarted)
        print(shared.settings["FPS"])

        # Modify a value.
        shared.restarted = False

        # Modify a mutable value such as a dictionary.
        settings = shared.settings
        settings["FPS"] = 144
        shared.settings = settings

    Notes:
        Values returned by ``__getattr__`` are local cached copies. Modifying
        a mutable value in place does not automatically update the shared
        state.

        For example, this does NOT update the shared dictionary::

            shared.settings["FPS"] = 144

        Instead, modify the local copy and assign it back::

            settings = shared.settings
            settings["FPS"] = 144
            shared.settings = settings
    """

    def __init__(self, manager: SyncManager) -> None:
        object.__setattr__(self, "_shared", manager.dict())
        object.__setattr__(self, "_local", {})
        object.__setattr__(self, "_dirty", {})

    def pull(self) -> None:
        """
        Mark all currently shared values as dirty.

        Dirty values are reloaded from the shared state on their next access.
        This allows multiple values to be refreshed at once while avoiding
        unnecessary reads until those values are actually used.
        """
        for name in list(self._shared.keys()):
            self._dirty[name] = True

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)

        # Pierwszy odczyt po pull()
        if self._dirty.get(name, True):
            try:
                self._local[name] = self._shared[name]
            except KeyError:
                raise AttributeError(
                    f"'SharedState' object has no attribute '{name}'"
                )

            self._dirty[name] = False

        try:
            return self._local[name]
        except KeyError:
            raise AttributeError(
                f"'SharedState' object has no attribute '{name}'"
            )

    def __setattr__(self, name, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return

        self._shared[name] = value
        self._local[name] = value
        self._dirty[name] = False
