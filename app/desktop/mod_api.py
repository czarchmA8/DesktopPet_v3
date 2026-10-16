from __future__ import annotations

import time
from bisect import bisect_right
from pathlib import Path
from dataclasses import replace as dataclasses_replace
from typing import Callable, Literal, cast

from PySide6.QtCore import QUrl, QRect, QPointF
from PySide6.QtGui import QColor, QPixmap, QImage, QImageReader, QCursor, QScreen, QPolygonF
from PySide6.QtWidgets import QApplication
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer, QVideoSink

from app.desktop.input_events import InputState, MouseButtonName, MouseButtonEvent, MouseScroll
from app.desktop.mods_manager import ModsManager, EntityMetadata, ModMetadata
import app.config as config
import app.logger as logger

class Animation:
    """Animation made of frames (GIF/APNG/WebP). It starts playing when loaded."""

    def __init__(self, frames: list[tuple[QPixmap, QImage]], ends: list[float], loop: bool) -> None:
        self.frames = frames
        self.ends = ends
        self.loop = loop
        self.speed = 1.0
        self._position = 0.0
        self._playing = True
        self._last = time.perf_counter()

    def _advance(self) -> None:
        now = time.perf_counter()
        if self._playing:
            self._position += (now - self._last) * self.speed
            total = self.ends[-1]
            if self.loop:
                self._position %= total
            elif self._position >= total:
                self._position = total
                self._playing = False
        self._last = now

    def play(self) -> None:
        """Plays the animation from the first frame."""
        self._position = 0.0
        self._last = time.perf_counter()
        self._playing = True

    def pause(self) -> None:
        """Freezes the animation on the current frame."""
        self._advance()
        self._playing = False

    def resume(self) -> None:
        """Continues a paused animation."""
        self._last = time.perf_counter()
        self._playing = True

    def stop(self) -> None:
        """Stops the animation and rewinds it to the first frame."""
        self._position = 0.0
        self._playing = False

    def set_speed(self, speed: float) -> None:
        """Sets the playback speed; 1.0 is normal, 2.0 twice as fast."""
        self._advance()
        self.speed = max(0.0, float(speed))

    def set_loop(self, loop: bool) -> None:
        """Turns looping on or off."""
        self.loop = bool(loop)

    def is_playing(self) -> bool:
        """Returns whether the animation is running (not paused, stopped or finished)."""
        self._advance()
        return self._playing

    def is_finished(self) -> bool:
        """Returns whether a non-looping animation has reached its last frame."""
        self._advance()
        return not self.loop and self._position >= self.ends[-1]

    def get_frame(self) -> tuple[QPixmap, QImage]:
        self._advance()
        return self.frames[min(bisect_right(self.ends, self._position), len(self.frames) - 1)]

class Video:
    """Video played by Qt. It starts playing when loaded."""

    def __init__(self, path: Path, loop: bool, volume: float = 1.0) -> None:
        self._QMediaPlayer = QMediaPlayer
        self._image: QImage | None = None
        self._frame: tuple[QPixmap, QImage] | None = None
        self._sink = QVideoSink()
        self._sink.videoFrameChanged.connect(self._on_frame)
        self._audio = QAudioOutput()
        self._audio.setVolume(volume)
        self._player = QMediaPlayer()
        self._player.setVideoSink(self._sink)
        self._player.setAudioOutput(self._audio)
        self.set_loop(loop)
        self._player.setSource(QUrl.fromLocalFile(str(path)))
        self._player.play()

    def _on_frame(self, frame) -> None:
        image = frame.toImage()
        if not image.isNull():
            self._image = image
            self._frame = None

    def get_frame(self) -> tuple[QPixmap, QImage] | None:
        if self._frame is None and self._image is not None:
            self._frame = (QPixmap.fromImage(self._image), self._image)
        return self._frame

    def play(self) -> None:
        """Plays the video from the beginning."""
        self._player.setPosition(0)
        self._player.play()

    def pause(self) -> None:
        """Freezes the video on the current frame."""
        self._player.pause()

    def resume(self) -> None:
        """Continues a paused video."""
        self._player.play()

    def stop(self) -> None:
        """Stops the video; nothing is drawn until `play()`."""
        self._player.stop()
        self._image = None
        self._frame = None

    def set_volume(self, volume: float) -> None:
        """Sets the volume, 0.0-1.0."""
        self._audio.setVolume(max(0.0, min(1.0, float(volume))))

    def set_speed(self, speed: float) -> None:
        """Sets the playback speed; 1.0 is normal, 2.0 twice as fast."""
        self._player.setPlaybackRate(max(0.01, float(speed)))

    def set_loop(self, loop: bool) -> None:
        """Turns looping on or off."""
        loops = self._QMediaPlayer.Loops
        self._player.setLoops(loops.Infinite if loop else loops.Once)

    def is_playing(self) -> bool:
        """Returns whether the video is playing right now."""
        return self._player.playbackState() == self._QMediaPlayer.PlaybackState.PlayingState

    def is_finished(self) -> bool:
        """Returns whether a non-looping video has reached its end."""
        return self._player.mediaStatus() == self._QMediaPlayer.MediaStatus.EndOfMedia

    def close(self) -> None:
        """Stops the video and releases the file. Call it in the entity's `delete_func`."""
        self._player.stop()
        self._player.setSource(QUrl())

class Sound:
    """Sound or music from a file (WAV, MP3, OGG...) played by Qt. It does not play until `play()` is called."""

    MAX_VOICES = 32
    """Most copies of the sound that can play at once with `play(overlap=True)`."""

    def __init__(self, path: Path, volume: float, loop: bool) -> None:
        self._QAudioOutput = QAudioOutput
        self._QMediaPlayer = QMediaPlayer
        self._path = path
        self._volume = volume
        self._loop = loop
        self._voices = [self._make_voice()]

    def _make_voice(self) -> tuple:
        loops = self._QMediaPlayer.Loops
        audio = self._QAudioOutput()
        audio.setVolume(self._volume)
        player = self._QMediaPlayer()
        player.setAudioOutput(audio)
        player.setLoops(loops.Infinite if self._loop else loops.Once)
        player.setSource(QUrl.fromLocalFile(str(self._path)))
        return player, audio

    def _is_playing(self, player) -> bool:
        return player.playbackState() == self._QMediaPlayer.PlaybackState.PlayingState

    def play(self, overlap: bool = False) -> None:
        """Plays the sound from the beginning.

        With `overlap=False` a sound that is already playing is restarted. With `overlap=True` it keeps playing and a
        new copy starts on top of it, up to `MAX_VOICES` copies; after that the first copy is restarted.
        """
        if overlap:
            player = next((p for p, _ in self._voices if not self._is_playing(p)), None)
            if player is None:
                if len(self._voices) < self.MAX_VOICES:
                    self._voices.append(self._make_voice())
                    player = self._voices[-1][0]
                else:
                    player = self._voices[0][0]
        else:
            for extra, _ in self._voices[1:]:
                extra.stop()
            player = self._voices[0][0]
        player.setPosition(0)
        player.play()

    def pause(self) -> None:
        """Pauses the sound; `resume()` continues it."""
        for player, _ in self._voices:
            player.pause()

    def resume(self) -> None:
        """Continues a paused sound."""
        for player, _ in self._voices:
            if player.playbackState() == self._QMediaPlayer.PlaybackState.PausedState:
                player.play()

    def stop(self) -> None:
        """Stops the sound, including all overlapping copies."""
        for player, _ in self._voices:
            player.stop()

    def set_volume(self, volume: float) -> None:
        """Sets the volume, 0.0-1.0."""
        self._volume = max(0.0, min(1.0, float(volume)))
        for _, audio in self._voices:
            audio.setVolume(self._volume)

    def set_loop(self, loop: bool) -> None:
        """Turns looping on or off."""
        self._loop = bool(loop)
        loops = self._QMediaPlayer.Loops
        for player, _ in self._voices:
            player.setLoops(loops.Infinite if self._loop else loops.Once)

    def is_playing(self) -> bool:
        """Returns whether any copy of the sound is playing right now."""
        return any(self._is_playing(player) for player, _ in self._voices)

    def close(self) -> None:
        """Stops the sound and releases the file. Call it in the entity's `delete_func`."""
        for player, _ in self._voices:
            player.stop()
            player.setSource(QUrl())
        self._voices = self._voices[:1]

class ModAPI:
    """The API object injected into every mod script; the interface between a mod and the application."""

    def __init__(self, mods_manager: ModsManager, mod_id: str) -> None:
        self._mods_manager: ModsManager = mods_manager
        self._mod_id: str = mod_id
        self._image_cache: dict[Path, tuple[QPixmap, QImage]] = {}
        self._animation_cache: dict[tuple[Path, float | None], tuple[list, list]] = {}

        self.Mod: ModMetadata = self._mods_manager.shared_data.active_mods[self._mod_id]

        self.Entity: ModAPI._Entity = self._Entity(self)
        self.Window: ModAPI._Window = self._Window(self)
        self.Overlay: ModAPI._Overlay = self._Overlay(self)
        self.Screen: ModAPI._Screen = self._Screen(self)
        self.Logger: ModAPI._Logger = self._Logger(self)
        self.Mouse: ModAPI._Mouse = self._Mouse(self)
        self.Media: ModAPI._Media = self._Media(self)

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

    @staticmethod
    def _normalize_points(points) -> QPolygonF:
        """Converts a list of (x, y) pairs into a QPolygonF."""
        polygon = QPolygonF()
        for point in (points.values() if hasattr(points, "values") else points):
            try:
                x, y = point.values() if hasattr(point, "values") else point
            except (TypeError, ValueError):
                raise ValueError("Polygon points must be (x, y) pairs") from None
            polygon.append(QPointF(x, y))
        return polygon

    _Color = str | tuple[int, int, int] | tuple[int, int, int, int]

    @property
    def settings(self) -> dict:
        return self._mods_manager.settings_snapshot

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
            self._mod_api._mods_manager.spawnable_entities[key] = EntityMetadata(
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
            return self._mod_api._mods_manager.shared_data.selected_entity_instance_id

        def is_selected(self, instance_id: str) -> bool:
            """Returns whether `instance_id` is the entity currently selected in the control panel."""
            return self._mod_api._mods_manager.shared_data.selected_entity_instance_id == instance_id

        def is_focused(self, hwnd: int, instance_id: str) -> bool:
            """Returns whether `hwnd` is active and `instance_id` is the selected entity."""
            return bool(self._mod_api.Window.is_focused(hwnd)) and self.is_selected(instance_id)

        def exists(self, instance_id: str) -> bool:
            """Returns whether the instance `instance_id` is currently spawned."""
            return instance_id in self._mod_api._mods_manager.displayed_entities_callbacks

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

    class _Window:
        """Windows and screens."""

        def __init__(self, mod_api: ModAPI) -> None:
            self._mod_api = mod_api

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

        def get_rect(self, hwnd: int) -> tuple[int, int, int, int] | None:
            """Returns the window rectangle (left, top, right, bottom) of `hwnd`."""
            rect = self._mod_api._mods_manager.overlay_manager.watcher.get_window_rect(hwnd)
            return cast(tuple[int, int, int, int], rect.as_tuple) if rect is not None else None

        def get_size(self, hwnd: int) -> tuple[int, int] | None:
            """Returns the (width, height) of the `hwnd` window."""
            rect = self._mod_api._mods_manager.overlay_manager.watcher.get_window_rect(hwnd)
            if rect is None:
                return None
            left, top, right, bottom = rect.as_tuple
            return cast(tuple[int, int], (right - left, bottom - top))
        
        def get_client_rect(self, hwnd: int) -> tuple[int, int, int, int] | None:
            """Returns the (left, top, right, bottom) rectangle of the client area of `hwnd` in screen coordinates:
            the part of the window without its title bar, borders and menu bar, where its content is drawn.
            A minimized window has an off-screen or empty client area."""
            rect = self._mod_api._mods_manager.overlay_manager.watcher.get_window_client_rect(hwnd)
            return cast(tuple[int, int, int, int], rect.as_tuple) if rect is not None else None

        def get_client_size(self, hwnd: int) -> tuple[int, int] | None:
            """Returns the (width, height) of the client area of `hwnd`."""
            rect = self._mod_api._mods_manager.overlay_manager.watcher.get_window_client_rect(hwnd)
            if rect is None:
                return None
            left, top, right, bottom = rect.as_tuple
            return cast(tuple[int, int], (right - left, bottom - top))

        def get_class_name(self, hwnd: int) -> str | None:
            """Returns the window class name of `hwnd`."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_window_class_name(hwnd)

        def get_process_id(self, hwnd: int) -> int | None:
            """Returns the id of the process that owns `hwnd`."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_window_process_id(hwnd)

        def get_process_name(self, hwnd: int) -> str | None:
            """Returns the file name of the program that owns `hwnd`, e.g. "chrome.exe", or None if the window does not
            exist or its process cannot be queried (protected system processes)."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_window_process_name(hwnd)

        def get_executable_path(self, hwnd: int) -> str | None:
            """Returns the full path of the program that owns `hwnd`, or None if
            the window does not exist or its process cannot be queried (protected system processes)."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_window_executable_path(hwnd)

        def get_windows(self, visible_only: bool = True) -> list[int]:
            """Returns the hwnds of all top-level windows, from the topmost to the bottommost in the z-order.
            With `visible_only` (default) hidden windows are skipped; minimized windows still count as visible.
            The list also contains helper and tool windows (many have an empty title) and may contain this
            application's own overlay windows, so filter it when you need real windows."""
            return self._mod_api._mods_manager.overlay_manager.watcher.get_all_windows(visible_only)

        def find_windows(self, title: str, exact: bool = False, case_sensitive: bool = False, visible_only: bool = True) -> list[int]:
            """Returns the hwnds of all top-level windows whose title contains `title` (or equals it with `exact`),
            from the topmost to the bottommost. The match ignores case unless `case_sensitive`. An empty `title` matches nothing."""
            return self._mod_api._mods_manager.overlay_manager.watcher.find_windows(title, exact, case_sensitive, visible_only)

        def find_window(self, title: str, exact: bool = False, case_sensitive: bool = False, visible_only: bool = True) -> int | None:
            """Returns the hwnd of the topmost window whose title contains `title` (or equals it with `exact`), or None."""
            matches = self.find_windows(title, exact, case_sensitive, visible_only)
            return matches[0] if matches else None

        def find_windows_by_process(self, process_name: str, visible_only: bool = True) -> list[int]:
            """Returns the hwnds of all top-level windows owned by a program called `process_name`, from the topmost to
            the bottommost. The match is on the executable file name and ignores case; a name without an extension also
            matches the file name without its extension ("notepad" matches "notepad.exe"). An empty name matches nothing."""
            return self._mod_api._mods_manager.overlay_manager.watcher.find_windows_by_process(process_name, visible_only)

        def find_window_by_process(self, process_name: str, visible_only: bool = True) -> int | None:
            """Returns the hwnd of the topmost window owned by a program called `process_name` (see `find_windows_by_process`), or None."""
            matches = self.find_windows_by_process(process_name, visible_only)
            return matches[0] if matches else None

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

    class _Overlay:
        """Drawing on window overlays."""

        def __init__(self, mod_api: ModAPI) -> None:
            self._mod_api = mod_api

        def draw_rect(self, hwnd: int | Literal["top"], x: int, y: int, width: int, height: int, color: ModAPI._Color="#ff0000", filled: bool=True, stroke_width: int=1, hit_id: str | None = None) -> None:
            """Draws a rectangle on the overlay of `hwnd` for the current frame."""
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("rect", x, y, width, height, qcolor, filled, stroke_width, hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_line(self, hwnd: int | Literal["top"], x1: int, y1: int, x2: int, y2: int, color: ModAPI._Color="#ffffff", width: int=1, hit_id: str | None = None) -> None:
            """Draws a line `width` pixels thick on the overlay of `hwnd` for the current frame. A `hit_id` makes it clickable."""
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("line", x1, y1, x2, y2, qcolor, width, hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_text(self, hwnd: int | Literal["top"], x: int, y: int, text: str, color: ModAPI._Color="#ffffff", size: int=12) -> None:
            """Draws text on the overlay of `hwnd` for the current frame. `y` is the baseline of the text and `size` is in points."""
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("text", x, y, str(text), qcolor, size)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_image(self, hwnd: int | Literal["top"], x: int, y: int, path: str, width: int | None = None, height: int | None = None, opacity: float = 1.0, hit_id: str | None = None) -> None:
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

        def draw_media(self, hwnd: int | Literal["top"], x: int, y: int, media: Animation | Video, width: int | None = None, height: int | None = None, opacity: float = 1.0, hit_id: str | None = None) -> None:
            """Draws the current frame of an `Animation` or `Video` (see `Media`) on the overlay of `hwnd` for the current frame.

            Parameters work like in `draw_image`. Draw it every frame to keep it playing; nothing is drawn while a video has no frame yet.
            """
            frame = media.get_frame()
            if frame is None:
                return
            pixmap, alpha_image = frame
            opacity = 1.0 if opacity is None else float(opacity)
            cmd = ("image", x, y, width, height, pixmap, opacity, alpha_image, hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_ellipse(self, hwnd: int | Literal["top"], x: int, y: int, width: int, height: int, color: ModAPI._Color="#ff0000", filled: bool=True, stroke_width: int=1, hit_id: str | None = None) -> None:
            """Draws an ellipse inscribed in the rectangle at (`x`, `y`) of size `width` x `height` on the overlay of `hwnd` for the current frame.

            Parameters work like in `draw_rect`; `stroke_width` is used only when `filled` is false. A `hit_id` makes the
            filled ellipse (or only its outline when not filled) clickable.
            """
            width, height = round(width), round(height)
            if width <= 0 or height <= 0:
                return
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("ellipse", round(x), round(y), width, height, qcolor, bool(filled), round(stroke_width), hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

        def draw_circle(self, hwnd: int | Literal["top"], x: int, y: int, radius: int, color: ModAPI._Color="#ff0000", filled: bool=True, stroke_width: int=1, hit_id: str | None = None) -> None:
            """Draws a circle with its center at (`x`, `y`) and the given `radius` on the overlay of `hwnd` for the current frame.

            Note that, unlike `draw_rect`, (`x`, `y`) is the center, not the top-left corner. The other parameters work like in
            `draw_ellipse`. Nothing is drawn if `radius` is not positive.
            """
            self.draw_ellipse(hwnd, x - radius, y - radius, radius * 2, radius * 2, color, filled, stroke_width, hit_id)

        def draw_polygon(self, hwnd: int | Literal["top"], points: list[tuple[int, int]], color: ModAPI._Color="#ff0000", filled: bool=True, stroke_width: int=1, hit_id: str | None = None) -> None:
            """Draws a closed polygon on the overlay of `hwnd` for the current frame.

            `points` is a list of at least 3 (x, y) pairs in screen coordinates; the last point is joined to the first
            automatically. Other parameters work like in `draw_rect`; a `hit_id` makes the filled polygon (or only its
            outline when not filled) clickable. Raises if there are fewer than 3 points or a point is not an (x, y) pair.
            """
            polygon = self._mod_api._normalize_points(points)
            if polygon.size() < 3:
                raise ValueError(f"{self._mod_api._mod_id}: a polygon needs at least 3 points")
            qcolor = self._mod_api._normalize_color(color)
            cmd = ("polygon", polygon, qcolor, bool(filled), round(stroke_width), hit_id)
            self._mod_api._mods_manager.overlay_manager.draw_commands.setdefault(hwnd, []).append(cmd)

    class _Screen:
        """Connected screens (monitors): size, available size (without the taskbar), position, count and more.

        Screens are addressed by index: 0 is the primary screen, the others follow in the order reported by the
        system. Indices can change when a monitor is connected or disconnected, so don't store them for long.
        Rectangles are (left, top, right, bottom) in the same screen coordinates as `Mouse.get_pos`, with exclusive
        right and bottom edges, like `Overlay.get_rect`. The "available" area is the screen without the taskbar
        and other areas reserved by the system. Methods taking an `index` return None if there is no such screen.
        """

        def __init__(self, mod_api: ModAPI) -> None:
            self._mod_api = mod_api

        @staticmethod
        def _get(index: int) -> QScreen | None:
            screens = QApplication.screens()
            return screens[index] if 0 <= index < len(screens) else None

        @staticmethod
        def _rect(rect: QRect) -> tuple[int, int, int, int]:
            return rect.x(), rect.y(), rect.x() + rect.width(), rect.y() + rect.height()

        def get_count(self) -> int:
            """Returns the number of connected screens."""
            return len(QApplication.screens())

        def get_name(self, index: int = 0) -> str | None:
            """Returns the name of screen `index`."""
            screen = self._get(index)
            return None if screen is None else screen.name()

        def get_rect(self, index: int = 0) -> tuple[int, int, int, int] | None:
            """Returns the full (left, top, right, bottom) rectangle of screen `index`."""
            screen = self._get(index)
            return None if screen is None else self._rect(screen.geometry())

        def get_size(self, index: int = 0) -> tuple[int, int] | None:
            """Returns the full (width, height) of screen `index`."""
            screen = self._get(index)
            if screen is None:
                return None
            geometry = screen.geometry()
            return geometry.width(), geometry.height()

        def get_available_rect(self, index: int = 0) -> tuple[int, int, int, int] | None:
            """Returns the (left, top, right, bottom) rectangle of screen `index` without the taskbar."""
            screen = self._get(index)
            return None if screen is None else self._rect(screen.availableGeometry())

        def get_available_size(self, index: int = 0) -> tuple[int, int] | None:
            """Returns the (width, height) of screen `index` without the taskbar."""
            screen = self._get(index)
            if screen is None:
                return None
            geometry = screen.availableGeometry()
            return geometry.width(), geometry.height()

        def get_virtual_rect(self) -> tuple[int, int, int, int]:
            """Returns the (left, top, right, bottom) rectangle of the whole virtual desktop (all screens together).
            `left` and `top` can be negative when a screen lies to the left of or above the primary one."""
            return self._rect(QApplication.primaryScreen().virtualGeometry())

        def get_virtual_size(self) -> tuple[int, int]:
            """Returns (width, height) of the whole virtual desktop."""
            virtual_rect = QApplication.primaryScreen().virtualGeometry()
            return virtual_rect.width(), virtual_rect.height()

        def get_index_at(self, x: int, y: int) -> int | None:
            """Returns the index of the screen containing the point (x, y), or None if it is outside all screens."""
            for index, screen in enumerate(QApplication.screens()):
                left, top, right, bottom = self._rect(screen.geometry())
                if left <= x < right and top <= y < bottom:
                    return index
            return None

        def get_scale_factor(self, index: int = 0) -> float | None:
            """Returns the display scaling of screen `index` (1.0 = 100%, 1.5 = 150%, ...)."""
            screen = self._get(index)
            return None if screen is None else screen.devicePixelRatio()

        def get_refresh_rate(self, index: int = 0) -> float | None:
            """Returns the refresh rate of screen `index` in Hz."""
            screen = self._get(index)
            return None if screen is None else screen.refreshRate()

        def get_info(self, index: int = 0) -> dict | None:
            """Returns everything known about screen `index` as a dict, or None."""
            screen = self._get(index)
            if screen is None:
                return None
            geometry, available = screen.geometry(), screen.availableGeometry()
            return {
                "index": index,
                "name": screen.name(),
                "is_primary": index == 0,
                "rect": self._rect(geometry),
                "size": (geometry.width(), geometry.height()),
                "available_rect": self._rect(available),
                "available_size": (available.width(), available.height()),
                "scale_factor": screen.devicePixelRatio(),
                "refresh_rate": screen.refreshRate(),
            }

    class _Media:
        """Loading animations, videos and sounds from the mod's own folder. Draw animations and videos with `Overlay.draw_media`."""

        def __init__(self, mod_api: ModAPI) -> None:
            self._mod_api = mod_api

        def load_animation(self, path: str, loop: bool = True, fps: float | None = None) -> Animation:
            """Loads an animated GIF/APNG/WebP. Every call returns an `Animation` with its own playback state (frames are shared); it starts playing at once.

            Frame delays come from the file; `fps` overrides them with a constant rate. Raises if the file cannot be loaded.
            """
            animation_path = self._mod_api._resolve_mod_path(path)
            key = (animation_path, fps)
            cached = self._mod_api._animation_cache.get(key)
            if cached is None:
                reader = QImageReader(str(animation_path))
                frames, ends, total = [], [], 0.0
                while reader.canRead():
                    image = reader.read()
                    if image.isNull():
                        break
                    delay_ms = 1000 / fps if fps else (reader.nextImageDelay() or 100)
                    total += delay_ms / 1000
                    frames.append((QPixmap.fromImage(image), image.convertToFormat(QImage.Format.Format_ARGB32)))
                    ends.append(total)
                if not frames:
                    raise Exception(f'{self._mod_api._mod_id}: could not load animation "{animation_path}"')
                cached = (frames, ends)
                self._mod_api._animation_cache[key] = cached
            return Animation(cached[0], cached[1], loop)

        def load_video(self, path: str, loop: bool = True, volume: float = 1.0) -> Video:
            """Loads a video. Call `close()` on it when the entity is deleted."""
            return Video(self._mod_api._resolve_mod_path(path), loop, volume)

        def load_sound(self, path: str, volume: float = 1.0, loop: bool = False) -> Sound:
            """Loads a sound; it does not play until `play()` is called. Call `close()` on it when the entity is deleted."""
            return Sound(self._mod_api._resolve_mod_path(path), max(0.0, min(1.0, float(volume))), loop)

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
