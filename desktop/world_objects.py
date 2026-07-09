from PySide6 import QtWidgets, QtCore, QtGui
import pymunk
import pymunk.autogeometry
import math
import win32gui, win32con
import ctypes
from ctypes import wintypes
import logging
from pathlib import Path
import json

from windows_layer import get_immediate_neighbors_above_and_below as get_immediate_neighbors_above_and_below
from logger_setup import setup_process_logger
from desktop.collisions import XYXY_Rectangle, CollisionTypes
from dashboard.objects_editor import generate_hull_vertices

logger: logging.Logger = logging.getLogger(__name__)

class WorldObject(QtWidgets.QWidget):
    '''Interactive physics object'''
    def __init__(
        self,
        shared_data,
        world_objects: list['WorldObject'],
        space: pymunk.Space,
        image_path: Path,
        start_x: int,
        start_y: int,
        vertices: list[tuple[float, float] | list[float]] | None=None,
        mass: float | None=None,
        elasticity: float | None=None,
        friction: float | None=None
    ) -> None:
        super().__init__()
        self.shared_data = shared_data
        self.world_objects = world_objects
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        self.original_pixmap = QtGui.QPixmap(image_path)
        self.rotated_pixmap = self.original_pixmap
        self.label = QtWidgets.QLabel(self)
        self.label.setPixmap(self.original_pixmap)
        self.w, self.h = self.original_pixmap.width(), self.original_pixmap.height()
        self.resize(self.w, self.h)

        object_settings_path = image_path.with_suffix(".json")
        raw_vertices: list[tuple[float, float] | list[float]] | list[tuple[float, float]] | list[list[float]]
        if object_settings_path.exists():
            with open(object_settings_path, "r", encoding="utf-8") as f:
                object_settings: dict = json.load(f)
            raw_vertices = vertices if vertices else object_settings["vertices"]
            mass = mass if mass else object_settings["mass"]
            elasticity = elasticity if elasticity else object_settings["elasticity"]
            friction = friction if friction else object_settings["friction"]
        else:
            raw_vertices = vertices if vertices else generate_hull_vertices(self.original_pixmap)
            mass = mass if mass else 10.0
            elasticity = elasticity if elasticity else 0.7
            friction = friction if friction else 0.3
            with open(object_settings_path, "w", encoding="utf-8") as f:
                json.dump({
                    "vertices": raw_vertices,
                    "mass": mass,
                    "elasticity": elasticity,
                    "friction": friction
                }, f, ensure_ascii=False)
            logger.debug(f"A new file \"{object_settings_path.name}\" has been created for the object")
        vertices_normalized: list[tuple[float, float]] = [(v[0], v[1]) for v in raw_vertices]

        self.hwnd_self = int(self.winId())

        # --- SPACE fizyki ---
        self.space: pymunk.Space = space

        # Platforma
        self.on_window_hwnd: int | None = None
        self.old_on_window_hwnd: int | None = None
        self.platform_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.platform_body.position = (0, -1000)
        self.platform_shape = pymunk.Poly.create_box(self.platform_body, (100, 1))
        self.platform_shape.elasticity = 0.5
        self.platform_shape.friction = 0.5
        self.platform_shape.collision_type = CollisionTypes.PLATFORM
        self.platform_shape.data = self.hwnd_self
        self.space.add(self.platform_body, self.platform_shape)
        self.old_window_rect: XYXY_Rectangle | None = None

        self.debug_expanded_platform_rect: XYXY_Rectangle | None = None

        # --- Ciało fizyczne ---
        moment = pymunk.moment_for_poly(mass, vertices_normalized)
        self.body = pymunk.Body(mass, moment)
        self.body.position = (start_x, start_y)
        self.shape = pymunk.Poly(self.body, vertices_normalized)
        self.shape.elasticity = elasticity
        self.shape.friction = friction
        self.shape.collision_type = CollisionTypes.OBJECT
        self.shape.data = self.hwnd_self
        self.space.add(self.body, self.shape)

        # --- Mouse body + joint (do przeciągania) ---
        self.mouse_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.space.add(self.mouse_body)

        self.mouse_joint: pymunk.PivotJoint | None = None
        self.is_dragging: bool = False

        self.pos_x: float = float(start_x)
        self.pos_y: float = float(start_y)
        self.angle, self.old_angle = 0.0, 0.0

    def tick(self, dt: float, window_XYXY_Rect: tuple[int, int, int, int]):
        '''Updates physics and visuals for world object'''
        window_rect: XYXY_Rectangle = XYXY_Rectangle(window_XYXY_Rect[0], window_XYXY_Rect[1], window_XYXY_Rect[2], window_XYXY_Rect[3])
        if self.old_window_rect is None or self.old_on_window_hwnd != self.on_window_hwnd:
            self.old_window_rect = window_rect
        expanded_platform_rect: XYXY_Rectangle = XYXY_Rectangle(
            min(window_rect.x, self.old_window_rect.x),
            min(window_rect.y, self.old_window_rect.y),
            max(window_rect.x2, self.old_window_rect.x2),
            max(window_rect.y, self.old_window_rect.y),
        )
        expanded_platform_rect = XYXY_Rectangle(
            int(min(expanded_platform_rect.x, expanded_platform_rect.x + int(self.body.velocity.x * dt))),
            expanded_platform_rect.y, # int(min(expanded_platform_rect.y, expanded_platform_rect.y + int(self.body.velocity.y * dt))) if self.body.position.y > expanded_platform_rect.y else expanded_platform_rect.y,
            math.ceil(max(expanded_platform_rect.x2, expanded_platform_rect.x2 + int(self.body.velocity.x * dt))),
            math.ceil(max(expanded_platform_rect.y2, expanded_platform_rect.y2 + int(self.body.velocity.y * 2 * dt))) if self.body.position.y < expanded_platform_rect.y2 else expanded_platform_rect.y2
        )
        # expanded_platform_rect = XYXY_Rectangle(
        #     expanded_platform_rect.x - 5,
        #     expanded_platform_rect.y - 5,
        #     expanded_platform_rect.x2 + 5,
        #     expanded_platform_rect.y2 + 5,
        # )
        self.debug_expanded_platform_rect = expanded_platform_rect

        vx = (window_rect.x - self.old_window_rect.x) / dt
        vy = (window_rect.y - self.old_window_rect.y) / dt
        self.platform_body.velocity = (vx, vy)

        # Zamiana wartości potrzebne do poprawnego funkcjonowania fizyki
        width, height = abs(expanded_platform_rect.x2 - expanded_platform_rect.x), abs(expanded_platform_rect.y2 - expanded_platform_rect.y)
        x, y = expanded_platform_rect.x + width // 2, expanded_platform_rect.y + height // 2
        # logger.debug(x, y, width, height)

        self.platform_body.position = x, y
        self.old_window_rect = window_rect

        # Aktualizacja rozmiaru i pozycji platformy (okna)
        self.space.remove(self.platform_shape)
        elasticity, friction = self.platform_shape.elasticity, self.platform_shape.friction
        self.platform_shape = pymunk.Poly.create_box(self.platform_body, (width, height))
        self.platform_shape.elasticity = elasticity
        self.platform_shape.friction = friction
        self.platform_shape.collision_type = CollisionTypes.PLATFORM
        self.platform_shape.data = self.hwnd_self
        self.space.add(self.platform_shape)

        # aktualizuj pozycję wizualną z ciała fizycznego
        self.pos_x, self.pos_y = self.body.position
        self.old_angle = self.angle
        self.angle = math.degrees(self.body.angle)
        self.update_visuals()
        self.old_on_window_hwnd = self.on_window_hwnd

        # Usuwanie obiektu jeżeli jest poza ekranami
        screen_geo = QtWidgets.QApplication.primaryScreen().virtualGeometry()
        if self.pos_x < screen_geo.left() - self.w or self.pos_x > screen_geo.right() + self.w or self.pos_y > screen_geo.bottom() + self.h:
            logger.info(f"Removed WorldObject: {self.hwnd_self}")
            self.world_objects.remove(self)
            self.space.remove(self.platform_body, self.platform_shape)
            self.space.remove(self.body, self.shape)
            self.close()
            self.deleteLater()

    def update_visuals(self) -> None:
        '''Updates visual position and rotation'''
        if self.pos_x is None or self.pos_y is None: return
        if math.isnan(self.pos_x) or math.isnan(self.pos_y): return

        if self.angle != self.old_angle:
            transform = QtGui.QTransform().rotate(self.angle)
            self.rotated_pixmap = self.original_pixmap.transformed(transform, QtCore.Qt.TransformationMode.SmoothTransformation)
            self.label.setPixmap(self.rotated_pixmap)
            self.label.adjustSize()
            self.resize(self.label.size())
        self.move(int(self.pos_x - self.rotated_pixmap.width() / 2), int(self.pos_y - self.rotated_pixmap.height() / 2))

    def mousePressEvent(self, event) -> None:
        '''Handles mouse press for dragging objects'''
        if event.button() == QtCore.Qt.MouseButton.LeftButton:
            m_pos = event.globalPosition()
            new_pos = pymunk.Vec2d(m_pos.x(), m_pos.y())

            self.mouse_body.position = new_pos

            local_anchor = self.body.world_to_local(new_pos)
            self.mouse_joint = pymunk.PivotJoint(self.mouse_body, self.body, (0, 0), local_anchor)
            self.mouse_joint.max_force = 1e6
            self.mouse_joint.error_bias = (1 - 0.15) ** 60 # przyspiesza stabilizację
            self.space.add(self.mouse_joint)

            self.is_dragging = True

            # Aktualizacja z-index obiektu
            above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(self.hwnd_self, True, [obj.hwnd_self for obj in self.world_objects] + [self.shared_data.pet["hwnd"]])
            if self.on_window_hwnd is not None and below_hwnd != self.on_window_hwnd:
                above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(self.on_window_hwnd, False, [obj.hwnd_self for obj in self.world_objects] + [self.shared_data.pet["hwnd"], self.on_window_hwnd])
                win32gui.SetWindowPos(self.hwnd_self, above_hwnd, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    def mouseMoveEvent(self, event) -> None:
        '''Handles mouse movement during drag'''
        if not self.is_dragging:
            return

        m_pos = event.globalPosition()
        self.mouse_body.position = pymunk.Vec2d(m_pos.x(), m_pos.y())

    def mouseReleaseEvent(self, event) -> None:
        '''Handles mouse release after drag'''
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False

            if self.mouse_joint is not None:
                try:
                    self.space.remove(self.mouse_joint)
                except Exception:
                    pass
                self.mouse_joint = None

            try:
                self.body.activate()
            except Exception:
                pass

            self.pos_x, self.pos_y = self.body.position
            self.angle = math.degrees(self.body.angle)

class WorldObjectsManager:
    def __init__(self, shared_data, log_queue) -> None:
        self.shared_data = shared_data

        global logger
        logger = setup_process_logger("world_objects", log_queue)
        logger.info("Creating the WorldObjectsManager...")

        self.world_objects: list[WorldObject] = []

        # Fizyka obiektów
        self.space = pymunk.Space()
        self.space.gravity = (0.0, 2000.0)
        self.space.on_collision(CollisionTypes.OBJECT, CollisionTypes.PLATFORM, pre_solve=self._platform_pre_solve, post_solve=self._platform_post_solve)

        # Podłoga ekranu
        screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.floor_shape = pymunk.Segment(self.space.static_body, (-10000, screen_geo.bottom()), (10000, screen_geo.bottom()), 5)
        self.floor_shape.elasticity, self.floor_shape.friction = 0.5, 1.0
        self.space.add(self.floor_shape)

        # Inicjalizacja funkcji API systemu Windows służące do zbiorczej aktualizacji z-index wielu okien w jednej operacji.
        self.user32 = ctypes.windll.user32
        HDWP = wintypes.HANDLE
        self.user32.BeginDeferWindowPos.argtypes = [ctypes.c_int]
        self.user32.BeginDeferWindowPos.restype = HDWP
        self.user32.DeferWindowPos.argtypes = [HDWP, wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user32.DeferWindowPos.restype = HDWP
        self.user32.EndDeferWindowPos.argtypes = [HDWP]
        self.user32.EndDeferWindowPos.restype = wintypes.BOOL

    def tick(self, dt, pet_hwnd) -> None:
        calculated_above_hwnds: dict[int, int | None] = {}
        ignored_hwnds = [obj.hwnd_self for obj in self.world_objects] + [pet_hwnd]
        hdwp = self.user32.BeginDeferWindowPos(len(self.world_objects))
        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        for object in self.world_objects:
            # --- Pobieranie hwnd okna pod obiektem ---
            if object.on_window_hwnd is None or not win32gui.IsWindow(object.on_window_hwnd):
                object.on_window_hwnd = get_immediate_neighbors_above_and_below(object.hwnd_self, True, ignored_hwnds)[1]
                logger.debug(f"Set new \"on_window_hwnd\" to {object.on_window_hwnd} ({win32gui.GetWindowText(object.on_window_hwnd)}) on object {object.hwnd_self}")

            on_window_hwnd = object.on_window_hwnd
            assert on_window_hwnd is not None

            if on_window_hwnd in calculated_above_hwnds:
                if calculated_above_hwnds[on_window_hwnd] is not None:
                    hdwp = self.user32.DeferWindowPos(hdwp, object.hwnd_self, calculated_above_hwnds[on_window_hwnd], 0, 0, 0, 0, flags)
                    # logger.debug(f"Zmiana warstwy obiektu {object.hwnd_self}")
            else:
                # --- Ustawianie warstwy okna obiektem ---
                # logger.debug(f"Sprawdzanie poprawnego z-index obiektu {object.hwnd_self}")
                above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(object.hwnd_self, True, ignored_hwnds)
                if below_hwnd == on_window_hwnd:
                    calculated_above_hwnds[on_window_hwnd] = None
                else:
                    above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(on_window_hwnd, False, ignored_hwnds)
                    calculated_above_hwnds[on_window_hwnd] = above_hwnd
                    hdwp = self.user32.DeferWindowPos(hdwp, object.hwnd_self, calculated_above_hwnds[on_window_hwnd], 0, 0, 0, 0, flags)
                    logger.debug(f"Set new \"on_window_hwnd\" to {object.on_window_hwnd} ({win32gui.GetWindowText(object.on_window_hwnd)}) on object {object.hwnd_self}")

        self.user32.EndDeferWindowPos(hdwp)

        window_rects: dict[int, tuple[int, int, int, int]] = {}
        for object in self.world_objects:
            # Pobieranie i zapisywanie rozmiarów okna `on_window_hwnd` danego obiektu, aby zmniejszyć liczbę wywołań `GetWindowRect`
            on_window_hwnd = object.on_window_hwnd
            assert on_window_hwnd is not None
            if on_window_hwnd not in window_rects:
                window_rects[on_window_hwnd] = win32gui.GetWindowRect(on_window_hwnd)
            object.tick(dt, window_rects[on_window_hwnd])
        self.space.step(dt)

    def _platform_pre_solve(self, arbiter, space, data) -> None: # Obiekty mogą przelatywać od dołu do góry przez platformę
        '''Collision callback - objects can pass through platform from below'''
        if arbiter.contact_point_set.normal.y < 0:
            arbiter.process_collision = False

        object_shape, platform_shape = arbiter.shapes
        if object_shape.data != platform_shape.data:
            arbiter.process_collision = False

    def _platform_post_solve(self, arbiter, space, data) -> None: # Obiekty po kolizji z platformą są teleportowane nad platformę
        '''Collision callback - objects teleported above platform after collision'''
        object_shape, platform_shape = arbiter.shapes
        object_body = object_shape.body

        platform_top_y = platform_shape.bb.bottom
        bottom_offset = object_shape.bb.top - object_body.position.y

        object_body.position = pymunk.Vec2d(object_body.position.x, platform_top_y - bottom_offset)

        if object_body.velocity.y > 0:
            object_body.velocity = pymunk.Vec2d(object_body.velocity.x, 0)

    def spawn_object(self, path: str) -> None:
        img_path = Path("Assets") / "Objects" / path
        if not img_path.exists():
            logger.error("[Obj] File not found:", img_path)

        x, y = win32gui.GetCursorPos()
        obj = WorldObject(self.shared_data, self.world_objects, self.space, img_path, x, y)
        self.world_objects.append(obj)
        obj.show()

    def clear_all_objects(self) -> None:
        for obj in list(self.world_objects):
            self.space.remove(obj.platform_body, obj.platform_shape)
            self.space.remove(obj.body, obj.shape)
            obj.deleteLater()
            obj.close()
        self.world_objects.clear()
