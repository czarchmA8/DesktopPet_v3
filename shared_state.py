from multiprocessing.managers import SyncManager

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
