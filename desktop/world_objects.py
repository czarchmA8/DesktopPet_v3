from PySide6 import QtWidgets, QtCore, QtGui
import pymunk
import pymunk.autogeometry
import math
import win32gui, win32con
import ctypes
from ctypes import wintypes
import logging

from windows_layer import get_immediate_neighbors_above_and_below as get_immediate_neighbors_above_and_below
from logger_setup import setup_process_logger
from desktop.collisions import XYXY_Rectangle, XYWH_Rectangle, CollisionTypes, CustomHitboxCollisions

logger: logging.Logger = None

class WorldObject(QtWidgets.QWidget):
    '''Interactive physics object'''
    def __init__(
        self,
        shared_data,
        world_objects: list['WorldObject'],
        space: pymunk.Space,
        image_path: str,
        start_x: int,
        start_y: int,
        mass: float=10.0,
        elasticity: float=0.4,
        friction: float=0.7
    ):
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

        self.hwnd_self = int(self.winId())

        # --- SPACE fizyki ---
        self.space: pymunk.Space = space

        # Platforma
        self.on_window_hwnd: int = None
        self.old_on_window_hwnd: int = None
        self.platform_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.platform_body.position = (0, -1000)
        self.platform_shape = pymunk.Poly.create_box(self.platform_body, (100, 1))
        self.platform_shape.elasticity = 0.5
        self.platform_shape.friction = 0.5
        self.platform_shape.collision_type = CollisionTypes.PLATFORM
        self.platform_shape.data = self.hwnd_self
        self.space.add(self.platform_body, self.platform_shape)
        self.old_window_rect: XYXY_Rectangle = None

        self.debug_expanded_platform_rect: XYXY_Rectangle = None

        # --- Ciało fizyczne ---
        hull: list[tuple[float, float]] = self.generate_hull_vertices(self.original_pixmap)
        moment = pymunk.moment_for_poly(mass, hull)
        self.body = pymunk.Body(mass, moment)
        self.body.position = (start_x, start_y)
        self.shape = pymunk.Poly(self.body, hull)
        self.shape.elasticity = elasticity
        self.shape.friction = friction
        self.shape.collision_type = CollisionTypes.OBJECT
        self.shape.data = self.hwnd_self
        self.space.add(self.body, self.shape)

        # --- Mouse body + joint (do przeciągania) ---
        self.mouse_body = pymunk.Body(body_type=pymunk.Body.KINEMATIC)
        self.space.add(self.mouse_body)

        self.mouse_joint: pymunk.PivotJoint = None
        self.is_dragging: bool = False

        self.pos_x, self.pos_y = start_x, start_y
        self.angle, self.old_angle = 0.0, 0.0

    def generate_hull_vertices(self, pixmap) -> list[pymunk.Vec2d] | list[tuple[float, float]]:
        '''Generates convex hull vertices from image transparency'''
        image = pixmap.toImage()
        width, height = image.width(), image.height()
        points = []
        for y in range(0, height, 1):
            for x in range(0, width, 1):
                if image.pixelColor(x, y).alpha() > 20:
                    points.append((x - width / 2, y - height / 2))
        return pymunk.autogeometry.to_convex_hull(points, 0) if points else [(-10, -10), (10, -10), (10, 10), (-10, 10)]

    def tick(self, dt: float, window_XYXY_Rect: tuple[int, int, int, int]):
        '''Updates physics and visuals for world object'''
        window_XYXY_Rect: XYXY_Rectangle = XYXY_Rectangle(window_XYXY_Rect[0], window_XYXY_Rect[1], window_XYXY_Rect[2], window_XYXY_Rect[3])
        if self.old_window_rect is None or self.old_on_window_hwnd != self.on_window_hwnd:
            self.old_window_rect = window_XYXY_Rect
        expanded_platform_rect: XYXY_Rectangle = XYXY_Rectangle(
            min(window_XYXY_Rect.x, self.old_window_rect.x),
            min(window_XYXY_Rect.y, self.old_window_rect.y),
            max(window_XYXY_Rect.x2, self.old_window_rect.x2),
            max(window_XYXY_Rect.y, self.old_window_rect.y),
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
        self.debug_expanded_platform_rect: XYXY_Rectangle = expanded_platform_rect

        vx = (window_XYXY_Rect.x - self.old_window_rect.x) / dt
        vy = (window_XYXY_Rect.y - self.old_window_rect.y) / dt
        self.platform_body.velocity = (vx, vy)

        # Zamiana wartości potrzebne do poprawnego funkcjonowania fizyki
        width, height = abs(expanded_platform_rect.x2 - expanded_platform_rect.x), abs(expanded_platform_rect.y2 - expanded_platform_rect.y)
        x, y = expanded_platform_rect.x + width // 2, expanded_platform_rect.y + height // 2
        # logger.debug(x, y, width, height)

        self.platform_body.position = x, y
        self.old_window_rect = window_XYXY_Rect

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

    def update_visuals(self):
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

    def mousePressEvent(self, event):
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
            if below_hwnd != self.on_window_hwnd:
                above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(self.on_window_hwnd, False, [obj.hwnd_self for obj in self.world_objects] + [self.shared_data.pet["hwnd"], self.on_window_hwnd])
                win32gui.SetWindowPos(self.hwnd_self, above_hwnd, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)

    def mouseMoveEvent(self, event):
        '''Handles mouse movement during drag'''
        if not self.is_dragging:
            return

        m_pos = event.globalPosition()
        self.mouse_body.position = pymunk.Vec2d(m_pos.x(), m_pos.y())

    def mouseReleaseEvent(self, event):
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
    def __init__(self, log_queue):
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

    def tick(self, dt, pet_hwnd):
        calculated_above_hwnds: dict[int, int | None] = {}
        ignored_hwnds = [obj.hwnd_self for obj in self.world_objects] + [pet_hwnd]
        hdwp = self.user32.BeginDeferWindowPos(len(self.world_objects))
        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        for object in self.world_objects:
            # --- Pobieranie hwnd okna pod obiektem ---
            if object.on_window_hwnd is None or not win32gui.IsWindow(object.on_window_hwnd):
                object.on_window_hwnd = get_immediate_neighbors_above_and_below(object.hwnd_self, True, ignored_hwnds)[1]
                logger.debug(f"Set new \"on_window_hwnd\" to {object.on_window_hwnd} ({win32gui.GetWindowText(object.on_window_hwnd)}) on object {object.hwnd_self}")

            if object.on_window_hwnd in calculated_above_hwnds:
                if calculated_above_hwnds[object.on_window_hwnd] is not None:
                    hdwp = self.user32.DeferWindowPos(hdwp, object.hwnd_self, calculated_above_hwnds[object.on_window_hwnd], 0, 0, 0, 0, flags)
                    # logger.debug(f"Zmiana warstwy obiektu {object.hwnd_self}")
            else:
                # --- Ustawianie warstwy okna obiektem ---
                # logger.debug(f"Sprawdzanie poprawnego z-index obiektu {object.hwnd_self}")
                above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(object.hwnd_self, True, ignored_hwnds)
                if below_hwnd == object.on_window_hwnd:
                    calculated_above_hwnds[object.on_window_hwnd] = None
                else:
                    above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(object.on_window_hwnd, False, ignored_hwnds)
                    calculated_above_hwnds[object.on_window_hwnd] = above_hwnd
                    hdwp = self.user32.DeferWindowPos(hdwp, object.hwnd_self, calculated_above_hwnds[object.on_window_hwnd], 0, 0, 0, 0, flags)
                    logger.debug(f"Set new \"on_window_hwnd\" to {object.on_window_hwnd} ({win32gui.GetWindowText(object.on_window_hwnd)}) on object {object.hwnd_self}")

        self.user32.EndDeferWindowPos(hdwp)

        window_rects: dict[int, tuple[int, int, int, int]] = {}
        for object in self.world_objects:
            # Pobieranie i zapisywanie rozmiarów okna `on_window_hwnd` danego obiektu, aby zmniejszyć liczbę wywołań `GetWindowRect`
            if object.on_window_hwnd not in window_rects:
                window_rects[object.on_window_hwnd] = win32gui.GetWindowRect(object.on_window_hwnd)
            object.tick(dt, window_rects[object.on_window_hwnd])
        self.space.step(dt)

    def _platform_pre_solve(self, arbiter, space, data): # Obiekty mogą przelatywać od dołu do góry przez platformę
        '''Collision callback - objects can pass through platform from below'''
        if arbiter.contact_point_set.normal.y < 0:
            arbiter.process_collision = False

        object_shape, platform_shape = arbiter.shapes
        if object_shape.data != platform_shape.data:
            arbiter.process_collision = False

    def _platform_post_solve(self, arbiter, space, data): # Obiekty po kolizji z platformą są teleportowane nad platformę
        '''Collision callback - objects teleported above platform after collision'''
        object_shape, platform_shape = arbiter.shapes
        object_body = object_shape.body

        platform_top_y = platform_shape.bb.bottom
        bottom_offset = object_shape.bb.top - object_body.position.y

        object_body.position = pymunk.Vec2d(object_body.position.x, platform_top_y - bottom_offset)

        if object_body.velocity.y > 0:
            object_body.velocity = pymunk.Vec2d(object_body.velocity.x, 0)
