from pathlib import Path

from PySide6.QtGui import QColor, QPixmap, QImage, QCursor

from desktop.input_events import InputState, MouseButtonName, MouseButtonEvent, MouseScroll
from desktop.mods_manager import ModsManager, Entity, Mod
import config
import logger

class ModAPI:
    """The API object injected into every mod script; the interface between a mod and the application."""

    def __init__(self, mods_manager: ModsManager, mod_id: str) -> None:
        self._mods_manager: ModsManager = mods_manager
        self._mod_id: str = mod_id
        self._image_cache: dict[Path, tuple[QPixmap, QImage]] = {}

        self.Mod: Mod = self._mods_manager.shared_data.active_mods[self._mod_id]
        self.Logger: ModAPI._Logger = self._Logger(self.Mod.id)
        self.Mouse: ModAPI._Mouse = self._Mouse(self._mods_manager)

    def _print(self, *args, sep: str=" ") -> None:
        """Logs `args` as a debug message, like Python's built-in `print`."""
        self.Logger.debug(sep.join(str(arg) for arg in args))

    def register_entity(self, entity_id: str, name: str, preview_path: str | None, description: str | None, create_func) -> None:
        """Registers an entity so it becomes spawnable from the control panel."""
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

    def get_real_window_above(self, hwnd: int) -> tuple[int | None, int | None]:
        """Returns a tuple containing:
        - hwnd of the nearest visible window above `hwnd` (skipping overlays), or None.
        - hwnd of the window directly above `hwnd` in the z-order, or None.
        """
        return self._mods_manager.overlay_manager.watcher.get_real_window_above(hwnd)

    def get_window_above(self, hwnd: int) -> int | None:
        """Returns the hwnd of the window directly above `hwnd` in the z-order, or None."""
        return self._mods_manager.overlay_manager.watcher.get_window_above(hwnd)

    def get_real_window_below(self, hwnd: int) -> tuple[int | None, int | None]:
        """Returns a tuple containing:
        - hwnd of the nearest visible window below `hwnd` (skipping overlays), or None.
        - hwnd of the window directly below `hwnd` in the z-order, or None.
        """
        return self._mods_manager.overlay_manager.watcher.get_real_window_below(hwnd)

    def get_window_below(self, hwnd: int) -> int | None:
        """Returns the hwnd of the window directly below `hwnd` in the z-order, or None."""
        return self._mods_manager.overlay_manager.watcher.get_window_below(hwnd)

    def get_window_rect(self, hwnd: int) -> tuple[int, int, int, int]:
        """Returns the (left, top, right, bottom) screen rectangle of `hwnd`."""
        return self._mods_manager.overlay_manager.watcher.get_window_rect(hwnd).as_tuple

    def get_foreground_window_hwnd(self) -> int:
        """Returns the hwnd of the current foreground (focused) window."""
        return self._mods_manager.overlay_manager.watcher.get_foreground_window_hwnd()

    def get_window_title(self, hwnd: int) -> str:
        """Returns the title text of `hwnd`."""
        return self._mods_manager.overlay_manager.watcher.get_window_title(hwnd)

    @staticmethod
    def _normalize_color(color) -> QColor:
        """Converts a hex string, an RGB(A) tuple/list, or a color-like object into a QColor."""
        if hasattr(color, "values"):
            return QColor(*(int(x) for x in color.values()))
        if isinstance(color, (tuple, list)):
            return QColor(*color)
        return QColor(color)

    def draw_rect(self, hwnd: int, x: int, y: int, width: int, height: int, color: str | tuple[int, int, int] | tuple[int, int, int, int]="#ff0000", filled: bool=True, hit_id: str | None = None) -> None:
        """Draws a rectangle on the overlay of `hwnd` for the current frame."""
        qcolor = self._normalize_color(color)
        cmd = ("rect", x, y, width, height, qcolor, filled, hit_id)
        self._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

    def draw_line(self, hwnd: int, x1: int, y1: int, x2: int, y2: int, color: str="#ffffff", width: int=1, hit_id: str | None = None) -> None:
        """Draws a line on the overlay of `hwnd` for the current frame."""
        qcolor = self._normalize_color(color)
        cmd = ("line", x1, y1, x2, y2, qcolor, width, hit_id)
        self._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

    def draw_text(self, hwnd: int, x: int, y: int, text: str, color: str="#ffffff", size: int=12) -> None:
        """Draws text on the overlay of `hwnd` for the current frame."""
        qcolor = self._normalize_color(color)
        cmd = ("text", x, y, str(text), qcolor, size)
        self._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

    def _resolve_mod_path(self, relative_path: str) -> Path:
        """Resolves a path a mod supplies against the mod's own folder."""
        mod_dir = (config.APP_DIR / "Mods" / self._mod_id).resolve()
        resolved = (mod_dir / relative_path).resolve()
        if not resolved.is_relative_to(mod_dir):
            raise ValueError(f'Path "{relative_path}" escapes the mod\'s own folder')
        return resolved

    def draw_image(self, hwnd: int, x: int, y: int, path: str, width: int | None = None, height: int | None = None, opacity: float = 1.0, hit_id: str | None = None) -> None:
        """Draws an image from a file inside the mod's own folder on the overlay of `hwnd` for the current frame."""
        opacity = 1.0 if opacity is None else float(opacity)

        image_path = self._resolve_mod_path(path)
        cached = self._image_cache.get(image_path)
        if cached is None:
            pixmap = QPixmap(str(image_path))
            if pixmap.isNull():
                self.Logger._log.warning(f'draw_image: could not load image "{image_path}"')
                return
            alpha_image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
            cached = (pixmap, alpha_image)
            self._image_cache[image_path] = cached

        pixmap, alpha_image = cached
        cmd = ("image", x, y, width, height, pixmap, opacity, alpha_image, hit_id)
        self._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

    class _Logger:
        """Per-mod logger; messages are written to the application's log files under this mod's ID."""

        def __init__(self, mod_id: str) -> None:
            self._mod_id: str = mod_id
            self._log = logger.get_logger(mod_id)

        def debug(self, text: str) -> None:
            """Logs a debug-level message."""
            self._log.debug(text)

        def info(self, text: str) -> None:
            """Logs an info-level message."""
            self._log.info(text)

        def warning(self, text: str) -> None:
            """Logs a warning-level message."""
            self._log.warning(text)

        def error(self, text: str) -> None:
            """Logs an error-level message."""
            self._log.error(text)

        def critical(self, text: str) -> None:
            """Logs a critical-level message."""
            self._log.critical(text)

    class _Mouse:
        """Mouse position, scroll and click/hit-testing for shapes drawn by this mod."""

        def __init__(self, mods_manager: ModsManager) -> None:
            self._mods_manager = mods_manager

        def _get_button_name(self, button: str) -> str:
            """Normalizes a button name or value to the internal button identifier."""
            for element in MouseButtonName:
                if button.lower() == element.name:
                    button = element.value
                    break
            return button

        def get_button_event(self, button: str) -> MouseButtonEvent | None:
            """Returns the current frame's event for `button`, or None if there is none."""
            return self._mods_manager.mouse_events.get(button, None)

        def is_entity_clicked(self, hit_id: str) -> bool:
            """Returns whether the shape with `hit_id` was just left-clicked this frame."""
            event = self.get_button_event(MouseButtonName.left)
            if event:
                return event.state == InputState.pressed and event.hit_id == hit_id
            else:
                return False

        def is_entity_pressed(self, button: str, hit_id: str) -> bool:
            """Returns whether `button` was just pressed down on the shape with `hit_id`."""
            button = self._get_button_name(button)
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.pressed and event.hit_id == hit_id
            else:
                return False

        def is_entity_holding(self, button: str, hit_id: str) -> bool:
            """Returns whether `button` is currently held down on the shape with `hit_id`."""
            button = self._get_button_name(button)
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.holding and event.hit_id == hit_id
            else:
                return False

        def is_entity_released(self, button: str, hit_id: str) -> bool:
            """Returns whether `button` was just released on the shape with `hit_id`."""
            button = self._get_button_name(button)
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.released and event.hit_id == hit_id
            else:
                return False

        def get_pos(self) -> tuple[int, int]:
            """Returns the current cursor position as (x, y) in screen coordinates."""
            pos = QCursor.pos()
            return pos.x(), pos.y()

        def get_scroll(self) -> MouseScroll:
            """Returns the current frame's scroll event."""
            return self._mods_manager.mouse_scroll

        def get_entity_scroll(self, hit_id: str) -> int:
            """Returns the vertical scroll amount over the shape with `hit_id` this frame."""
            if self._mods_manager.mouse_scroll.hit_id == hit_id:
                return self._mods_manager.mouse_scroll.y
            else:
                return 0

        def get_entity_scroll_x(self, hit_id: str) -> int:
            """Returns the horizontal scroll amount over the shape with `hit_id` this frame."""
            if self._mods_manager.mouse_scroll.hit_id == hit_id:
                return self._mods_manager.mouse_scroll.x
            else:
                return 0

    def is_entity_focused(self, instance_id: str) -> bool:
        """Returns whether `instance_id` is the entity currently selected in the control panel."""
        return self._mods_manager.shared_data.selected_entity == instance_id

    def is_window_focused(self, hwnd: int) -> bool | None:
        """Returns whether `hwnd` is the active window, or None if it has no overlay window."""
        window = self._mods_manager.overlay_manager.transparent_windows.get(hwnd, None)
        if window:
            return window.isActiveWindow()
        else:
            return None

    def is_focused(self, hwnd: int, instance_id: str) -> bool:
        """Returns whether `hwnd` is active and `instance_id` is the selected entity."""
        return bool(self.is_window_focused(hwnd)) and self.is_entity_focused(instance_id)

    def kill_entity(self, instance_id: str) -> None:
        """Removes the entity instance `instance_id`."""
        self._mods_manager.kill_entity(instance_id)

if __name__ == "__main__":
    from tools.generate_lua_stubs import write_stub as write_lua_stub
    from tools.generate_python_stubs import write_stub as write_python_stub
    write_lua_stub()
    write_python_stub()
