from __future__ import annotations

from pathlib import Path
from dataclasses import replace as dataclasses_replace
from typing import Callable

from PySide6.QtGui import QColor, QPixmap, QImage, QCursor
from PySide6.QtWidgets import QApplication

from app.desktop.input_events import InputState, MouseButtonName, MouseButtonEvent, MouseScroll
from app.desktop.mods_manager import ModsManager, Entity, Mod
import app.config as config
import app.logger as logger

class ModAPI:
    """The API object injected into every mod script; the interface between a mod and the application."""

    def __init__(self, mods_manager: ModsManager, mod_id: str) -> None:
        self._mods_manager: ModsManager = mods_manager
        self._mod_id: str = mod_id
        self._image_cache: dict[Path, tuple[QPixmap, QImage]] = {}

        self.Mod: Mod = self._mods_manager.shared_data.active_mods[self._mod_id]

        self.Entity: ModAPI._Entity = self._Entity(self)
        self.Overlay: ModAPI._Overlay = self._Overlay(self)
        self.Logger: ModAPI._Logger = self._Logger(self)
        self.Mouse: ModAPI._Mouse = self._Mouse(self)

    def _print(self, *args, sep: str=" ") -> None:
        """Logs `args` as a debug message, like Python's built-in `print`."""
        self.Logger.debug(sep.join(str(arg) for arg in args))

    def _resolve_mod_path(self, relative_path: str) -> Path:
        """Resolves a path a mod supplies against the mod's own folder."""
        mod_dir = (config.APP_DIR / "Mods" / self._mod_id).resolve()
        resolved = (mod_dir / relative_path).resolve()
        if not resolved.is_relative_to(mod_dir):
            raise ValueError(f'Path "{relative_path}" escapes the mod\'s own folder')
        return resolved

    @staticmethod
    def _normalize_color(color) -> QColor:
        """Converts a hex string, an RGB(A) tuple/list, or a color-like object into a QColor."""
        if hasattr(color, "values"):
            return QColor(*(int(x) for x in color.values()))
        if isinstance(color, (tuple, list)):
            return QColor(*color)
        return QColor(color)

    _Color = str | tuple[int, int, int] | tuple[int, int, int, int]

    class _Entity:
        """Registering, spawning and removing entities, selection, and clicks on shapes drawn with a hit_id."""

        def __init__(self, mod_api: ModAPI):
            self._mod_api = mod_api

        def register(self, entity_id: str, name: str, preview_path: str | None, description: str | None, create_func: Callable[[str], dict[str, Callable]]) -> None:
            """Registers an entity so it becomes spawnable from the control panel.

            `entity_id` must be unique within the mod. `preview_path` is relative to the mod folder (or None) and raises
            an error if it leaves that folder.

            `create_func(instance_id)` is called for every spawned instance. It must return a table/dict of callbacks
            (the table/dict may be empty, every callback is optional):
            - `tick_func(dt, hitbox_overlay)`: every frame while the instance exists. `dt` is the time since the
              previous frame in seconds, `hitbox_overlay` is true when debug mode and the hitbox overlay are enabled.
            - `show_func()`, `hide_func()`, `teleport_func()`: the user shows, hides or teleports the entity in the
              control panel.
            - `get_info_func()`: every frame while the entity is selected; returns a table/dict shown as its details.
            - `delete_func()`: the instance is removed, from the control panel or with `kill`."""
            key = f"{self._mod_api._mod_id}:{entity_id}"
            self._mod_api._mods_manager.spawnable_entities[key] = Entity(
                id=entity_id,
                name=name,
                mod_id=self._mod_api._mod_id,
                preview_path=self._mod_api._resolve_mod_path(preview_path) if preview_path else None,
                description=description if description else "No description available."
            )
            self._mod_api._mods_manager.entity_factories[key] = create_func
            self._mod_api._mods_manager.spawnable_entities_dirty = True

        def get_selected(self) -> str | None:
            """Returns the `instance_id` of the entity selected in the control panel, or None."""
            return self._mod_api._mods_manager.shared_data.selected_entity

        def is_selected(self, instance_id: str) -> bool:
            """Returns whether `instance_id` is the entity currently selected in the control panel."""
            return self._mod_api._mods_manager.shared_data.selected_entity == instance_id

        def is_focused(self, hwnd: int, instance_id: str) -> bool:
            """Returns whether `hwnd` is active and `instance_id` is the selected entity."""
            return bool(self._mod_api.Overlay.is_focused(hwnd)) and self.is_selected(instance_id)

        def exists(self, instance_id: str) -> bool:
            """Returns whether the instance `instance_id` is currently spawned."""
            return instance_id in self._mod_api._mods_manager.displayed_entities

        def spawn(self, entity_id: str) -> str | None:
            """Spawns a new instance of an entity and returns its `instance_id`, or None if it is not registered."""
            return self._mod_api._mods_manager.spawn_entity(self._mod_api._mod_id, entity_id)

        def kill(self, instance_id: str) -> None:
            """Removes the entity instance `instance_id` and calls its `delete_func`."""
            self._mod_api._mods_manager.kill_entity(instance_id)

        # --- Mouse ---

        def is_pressed(self, button: str, hit_id: str) -> bool:
            """Returns whether `button` went down on the shape with `hit_id`."""
            event = self._mod_api.Mouse.get_button_event(button)
            if event:
                return event.state == InputState.pressed and event.hit_id == hit_id
            else:
                return False

        def is_holding(self, button: str, hit_id: str) -> bool:
            """Returns whether `button` is held down, having been pressed on the shape with `hit_id` (also when the cursor left it)."""
            event = self._mod_api.Mouse.get_button_event(button)
            if event:
                return event.state == InputState.holding and event.hit_id == hit_id
            else:
                return False

        def is_released(self, button: str, hit_id: str) -> bool:
            """Returns whether `button` was released over the shape with `hit_id`."""
            event = self._mod_api.Mouse.get_button_event(button)
            if event:
                return event.state == InputState.released and event.hit_id == hit_id
            else:
                return False

        def get_scroll_y(self, hit_id: str) -> int:
            """Returns the vertical scroll of this frame if the cursor is over the shape with `hit_id`, otherwise 0."""
            if self._mod_api._mods_manager.mouse_scroll.hit_id == hit_id:
                return self._mod_api._mods_manager.mouse_scroll.y
            else:
                return 0

        def get_scroll_x(self, hit_id: str) -> int:
            """Returns the horizontal scroll of this frame if the cursor is over the shape with `hit_id`, otherwise 0."""
            if self._mod_api._mods_manager.mouse_scroll.hit_id == hit_id:
                return self._mod_api._mods_manager.mouse_scroll.x
            else:
                return 0

    class _Overlay:
        """Windows, screens and drawing on window overlays."""

        def __init__(self, mod_api: ModAPI):
            self._mod_api = mod_api

        # --- Window ---

        def exists(self, hwnd: int) -> bool:
            """Returns whether `hwnd` is still a valid window."""
            return self._mod_api._mods_manager.overlay_manager.watcher.window_exists(hwnd)

        def is_visible(self, hwnd: int) -> bool | None:
            """Returns whether `hwnd` has the visible style (a minimized window still counts as visible)."""
            return self._mod_api._mods_manager.overlay_manager.watcher.is_window_visible(hwnd)

        def is_minimized(self, hwnd: int) -> bool | None:
            """Returns whether `hwnd` is minimized."""
            return self._mod_api._mods_manager.overlay_manager.watcher.is_window_minimized(hwnd)

        def is_maximized(self, hwnd: int) -> bool | None:
            """Returns whether `hwnd` is maximized."""
            return self._mod_api._mods_manager.overlay_manager.watcher.is_window_maximized(hwnd)

        def is_fullscreen(self, hwnd: int) -> bool | None:
            """Returns whether `hwnd` covers its whole screen, including the taskbar area."""
            return self._mod_api._mods_manager.overlay_manager.watcher.is_window_fullscreen(hwnd)

        def is_focused(self, hwnd: int) -> bool | None:
            """Returns whether `hwnd` is the active, foreground or focused window."""
            return self._mod_api._mods_manager.overlay_manager.watcher.is_window_foreground(hwnd)

        def get_title(self, hwnd: int) -> str | None:
            """Returns the title text of `hwnd`."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_window_title(hwnd)

        def get_rect(self, hwnd: int) -> tuple[int | float, int | float, int | float, int | float] | None:
            """Returns the (left, top, right, bottom) screen rectangle of `hwnd`."""
            rect = self._mod_api._mods_manager.overlay_manager.watcher.get_window_rect(hwnd)
            return rect.as_tuple if rect is not None else None

        def get_primary_screen_size(self) -> tuple[int, int]:
            """Returns (width, height) of the primary screen."""
            primary_screen = QApplication.primaryScreen()
            geometry = primary_screen.geometry()
            return geometry.width(), geometry.height()

        def get_virtual_screen_size(self) -> tuple[int, int]:
            """Returns (width, height) of the whole virtual desktop."""
            primary_screen = QApplication.primaryScreen()
            virtual_rect = primary_screen.virtualGeometry()
            return virtual_rect.width(), virtual_rect.height()

        # --- Z-order ---

        def get_real_window_above(self, hwnd: int) -> tuple[int | None, int | None]:
            """Returns a tuple containing:
            - hwnd of the nearest visible window above `hwnd` (skipping overlays), or None.
            - hwnd of the window directly above `hwnd` in the z-order, or None.
            """
            return self._mod_api._mods_manager.overlay_manager.watcher.get_real_window_above(hwnd)

        def get_window_above(self, hwnd: int) -> int | None:
            """Returns the hwnd of the window directly above `hwnd` in the z-order, or None."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_window_above(hwnd)

        def get_real_window_below(self, hwnd: int) -> tuple[int | None, int | None]:
            """Returns a tuple containing:
            - hwnd of the nearest visible window below `hwnd` (skipping overlays), or None.
            - hwnd of the window directly below `hwnd` in the z-order, or None.
            """
            return self._mod_api._mods_manager.overlay_manager.watcher.get_real_window_below(hwnd)

        def get_window_below(self, hwnd: int) -> int | None:
            """Returns the hwnd of the window directly below `hwnd` in the z-order, or None."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_window_below(hwnd)

        def get_foreground_hwnd(self) -> int:
            """Returns the hwnd of the current foreground (focused) window."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_foreground_window_hwnd()

        # --- Drawing ---

        def draw_rect(self, hwnd: int, x: int, y: int, width: int, height: int, color: ModAPI._Color="#ff0000", filled: bool=True, stroke_width: int=1, hit_id: str | None = None) -> None:
            """Draws a rectangle on the overlay of `hwnd` for the current frame."""
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("rect", x, y, width, height, qcolor, filled, stroke_width, hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_line(self, hwnd: int, x1: int, y1: int, x2: int, y2: int, color: ModAPI._Color="#ffffff", width: int=1, hit_id: str | None = None) -> None:
            """Draws a line `width` pixels thick on the overlay of `hwnd` for the current frame. A `hit_id` makes it clickable."""
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("line", x1, y1, x2, y2, qcolor, width, hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_text(self, hwnd: int, x: int, y: int, text: str, color: ModAPI._Color="#ffffff", size: int=12) -> None:
            """Draws text on the overlay of `hwnd` for the current frame. `y` is the baseline of the text and `size` is in points."""
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("text", x, y, str(text), qcolor, size)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_image(self, hwnd: int, x: int, y: int, path: str, width: int | None = None, height: int | None = None, opacity: float = 1.0, hit_id: str | None = None) -> None:
            """Draws an image from a file inside the mod's own folder on the overlay of `hwnd` for the current frame.

            If only `width` or `height` is given the aspect ratio is kept. `opacity` is 0.0-1.0. Images are cached after the
            first load. Raises if the path leaves the mod folder or the image cannot be loaded. A `hit_id` makes the
            non-transparent pixels clickable.
            """
            opacity = 1.0 if opacity is None else float(opacity)

            image_path = self._mod_api._resolve_mod_path(path)
            cached = self._mod_api._image_cache.get(image_path)
            if cached is None:
                pixmap = QPixmap(str(image_path))
                if pixmap.isNull():
                    raise Exception(f'{self._mod_api._mod_id}: could not load image "{image_path}"')
                alpha_image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
                cached = (pixmap, alpha_image)
                self._mod_api._image_cache[image_path] = cached

            pixmap, alpha_image = cached
            cmd = ("image", x, y, width, height, pixmap, opacity, alpha_image, hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

    class _Logger:
        """Per-mod logger; messages are written to the application's log files under this mod's ID."""

        def __init__(self, mod_api: ModAPI) -> None:
            self._mod_api = mod_api
            self._log = logger.get_logger(self._mod_api._mod_id)

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
        """Cursor position, button state and scroll, regardless of what is under the cursor.

        Buttons: `left`, `middle`, `right`, `forward`, `back`. Clicks on a specific shape (drawn with a `hit_id`) are in
        `Entity`: `is_pressed`, `is_holding`, `is_released`.
        """

        def __init__(self, mod_api: ModAPI) -> None:
            self._mod_api = mod_api

        def _get_button_name(self, button: str) -> str:
            """Normalizes a button name or value to the internal button identifier."""
            for element in MouseButtonName:
                if button.lower() == element.name:
                    button = element.value
                    break
            return button

        def get_button_event(self, button: str) -> MouseButtonEvent | None:
            """Returns the current frame's event for `button`, or None if there is none."""
            button = self._get_button_name(button)
            event = self._mod_api._mods_manager.mouse_events.get(button, None)
            return None if event is None else dataclasses_replace(event)

        def is_pressed(self, button: str) -> bool:
            """Returns whether `button` went down this frame, anywhere on the screen."""
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.pressed
            else:
                return False

        def is_holding(self, button: str) -> bool:
            """Returns whether `button` is held down, anywhere on the screen."""
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.holding
            else:
                return False

        def is_released(self, button: str) -> bool:
            """Returns whether `button` was released this frame, anywhere on the screen."""
            event = self.get_button_event(button)
            if event:
                return event.state == InputState.released
            else:
                return False

        def get_pos(self) -> tuple[int, int]:
            """Returns the current cursor position as (x, y) in screen coordinates."""
            pos = QCursor.pos()
            return pos.x(), pos.y()

        def get_scroll(self) -> MouseScroll:
            """Returns the current frame's scroll event."""
            return dataclasses_replace(self._mod_api._mods_manager.mouse_scroll)

        def get_scroll_y(self) -> int:
            """Returns the vertical scroll of this frame, anywhere on the screen."""
            return self._mod_api._mods_manager.mouse_scroll.y

        def get_scroll_x(self) -> int:
            """Returns the horizontal scroll of this frame, anywhere on the screen."""
            return self._mod_api._mods_manager.mouse_scroll.x
