import os
import random
import sys
import time
from PyQt6 import QtWidgets, QtCore, QtGui
import win32gui, win32con
import ctypes
from ctypes import wintypes
import math
import pymunk
import pymunk.autogeometry
from dataclasses import dataclass
from enum import IntEnum, auto
import logging

from windows_layer import get_immediate_neighbors_above_and_below as get_immediate_neighbors_above_and_below
from windows_layer import is_real_window as is_real_window
import debug_overlay
from logger_setup import setup_process_logger

logger: logging.Logger = None

class CustomHitboxCollisions:
    '''Utility class for custom collision detection'''
    @staticmethod
    def check_rect_hitbox_collision(rect, rect2) -> bool:
        '''Checks if two rectangles collide'''
        x1, y1, x2, y2 = rect
        a1, b1, a2, b2 = rect2

        if x2 < a1 or a2 < x1:
            return False
        if y2 < b1 or b2 < y1:
            return False

        return True

    @staticmethod
    def check_pixel_solid(hitbox_x, hitbox_y, hitbox, global_x, global_y) -> bool:
        '''Checks if hitbox collide with pixel at given position'''
        # Przeliczanie współrzędnych globalnych na lokalne współrzędne obrazka
        local_x = int(global_x - hitbox_x)
        local_y = int(global_y - hitbox_y)

        current_frame = hitbox.currentImage()

        width = current_frame.width()
        height = current_frame.height()

        # Sprawdź czy punkt mieści się w wymiarach obrazka
        if 0 <= local_x < width and 0 <= local_y < height:
            pixel_color = current_frame.pixelColor(local_x, local_y)
            return pixel_color.alpha() > 0

        return False

    @staticmethod
    def check_hitbox_collision(pos1, img1, pos2, img2) -> bool:
        """
        Pixel-perfect collision detection between two images

        pos1, pos2: krotki (x, y) lewego górnego rogu
        img1, img2: obiekty QImage (maski hitboxów)
        """
        rect1 = QtCore.QRect(pos1[0], pos1[1], img1.width(), img1.height())
        rect2 = QtCore.QRect(pos2[0], pos2[1], img2.width(), img2.height())

        intersection = rect1.intersected(rect2)
        if intersection.isEmpty():
            return False

        for x in range(intersection.left(), intersection.right() + 1):
            for y in range(intersection.top(), intersection.bottom() + 1):
                local_x1 = x - rect1.x()
                local_y1 = y - rect1.y()
                local_x2 = x - rect2.x()
                local_y2 = y - rect2.y()

                # Sprawdzamy czy OBA piksele są nieprzezroczyste (alpha > 0)
                pixel1_alpha = img1.pixelColor(local_x1, local_y1).alpha()
                pixel2_alpha = img2.pixelColor(local_x2, local_y2).alpha()

                if pixel1_alpha > 0 and pixel2_alpha > 0:
                    return True

        return False

class CollisionTypes(IntEnum):
    '''Enumeration of collision types (OBJECT, PLATFORM)'''
    OBJECT = auto()
    PLATFORM = auto()

@dataclass
class XYXY_Rectangle:
    '''Rectangle defined by (x, y, x2, y2) coordinates'''
    x: int
    y: int
    x2: int
    y2: int

    @property
    def as_tuple(self) -> tuple[int, int, int, int]:
        """Returns rectangle as a clean tuple (x, y, x2, y2)"""
        return (self.x, self.y, self.x2, self.y2)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.x2
        yield self.y2

@dataclass
class XYWH_Rectangle:
    '''Rectangle defined by (x, y, width, height)'''
    x: int
    y: int
    width: int
    height: int

    @property
    def as_tuple(self) -> tuple[int, int, int, int]:
        """Returns rectangle as a clean tuple (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.width
        yield self.height

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
            math.ceil(max(expanded_platform_rect.y2, expanded_platform_rect.y2 + int(self.body.velocity.y * dt))) * 2 if self.body.position.y < expanded_platform_rect.y2 else expanded_platform_rect.y2
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
            logger.info(f"[Obj] Removed WorldObject: {self.hwnd_self}")
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

class PetWidget(QtWidgets.QWidget):
    '''Main pet character widget with physics and animation'''
    def __init__(self, conn, shared_data):
        super().__init__()
        self.conn = conn
        self.shared_data = shared_data
        self.world_objects: list[WorldObject] = []

        # Ustawianie atrybutów okna (tytuł, flagi itp.)
        self.setWindowTitle("Charmander")
        self.setWindowFlags(QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Tool)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)

        self.hwnd_self = int(self.winId())
        logger.info(f"[Pet] hwnd: {self.hwnd_self} ({win32gui.GetWindowText(self.hwnd_self)})")

        # Ładowanie animacji i hitboxu
        self.animations: dict = {}
        self.hitbox_animations: dict = {}
        for filename in os.listdir("Assets\\animations"):
            if filename.endswith("_hitbox.gif"):
                continue

            self.animations[filename] = QtGui.QMovie(f"Assets\\animations\\{filename}")
            self.animations[filename].setCacheMode(QtGui.QMovie.CacheMode.CacheAll)

            # base_name = os.path.splitext(plik)[0]
            # ext = os.path.splitext(plik)[1]
            # hitbox_file = f"{base_name}_hitbox{ext}"
            hitbox_file = filename

            self.hitbox_animations[filename] = QtGui.QMovie(f"Assets\\animations\\{hitbox_file}")
            self.hitbox_animations[filename].setCacheMode(QtGui.QMovie.CacheMode.CacheAll)

        # Ustawianie wagi zadań
        @dataclass
        class TaskContainer:
            weights: list[int]
            names: list[str]

        self.tasks = [(4, "Walking"), (2, "Standing"), (2, "Sitting"), (0, "Change window"), (1, "Sleeping")]
        weights: list[int] = [weight for weight, _ in self.tasks]
        names: list[str] = [task_name for _, task_name in self.tasks]
        self.tasks: TaskContainer = TaskContainer(weights, names)
        total_task_weight = sum(self.tasks.weights)
        logger.debug(f"[Pet] Total task weight: {total_task_weight}")
        for weight, task_name in sorted(zip(self.tasks.weights, self.tasks.names)):
            logger.debug(f"[Pet] {task_name}: {round(weight / total_task_weight * 100, 1)}%")

        self.current_task: str = "Falling"
        self.pet_label = QtWidgets.QLabel(self)
        self.current_animation: str = None
        self.orientation: str = "left"
        self.task_end_time: float = time.perf_counter()
        self.set_animation("left_falling.gif")

        # Stan okien / platformy
        self.on_window_hwnd: int = None
        self.old_on_window_hwnd: int = None
        self.old_window_rect: XYXY_Rectangle = None

        # Pasek zadań: ziemia ma być NAD paskiem zadań
        self.taskbar_y: int = QtWidgets.QApplication.primaryScreen().availableGeometry().bottom()

        # Fizyka obiektów
        self.space = pymunk.Space()
        self.space.gravity = (0.0, 2000.0)
        self.space.on_collision(CollisionTypes.OBJECT, CollisionTypes.PLATFORM, pre_solve=self._platform_pre_solve, post_solve=self._platform_post_solve)

        # Podłoga ekranu
        screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        self.floor_shape = pymunk.Segment(self.space.static_body, (-10000, screen_geo.bottom()), (10000, screen_geo.bottom()), 5)
        self.floor_shape.elasticity, self.floor_shape.friction = 0.5, 1.0
        self.space.add(self.floor_shape)

        # Ruch i fizyka
        self.velocity: list = [400.0, 0.0]
        self.mass = 1.0
        self.gravity = 2500.0
        self.drag_air_k = 0.0015
        self.mu_kinetic: float = 0.9
        self.mu_static: float = 1.5
        self.min_vx_threshold = 1.0
        self.restitution = 0.45

        self.is_dragging: bool = False
        self.real_x, self.real_y = self.x(), self.y()
        self.old_real_x, self.old_real_y = self.real_x, self.real_y
        self.on_ground: bool = False
        self.on_window: bool = False

        # Hitbox stóp (GIF 256x256)
        self.foot_x: int = 96
        self.foot_y: int = 176
        self.foot_width: int = 48

        # Pet współdzielone informacje
        self.shared_data.pet = {
            "hwnd": self.hwnd_self,
            "stats": {
                "fitness": 100,
                "friendship": 100,
                "happiness": 100,
                "comfort": 100,
                "hunger": 100,
                "thirst": 100,
                "energy": 100,
                "cleanliness": 100,
                "warmth": 100,
                "attention": 100,
                "playfulness": 100,
            }
        }

        # Timer / dt
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(1000 // self.shared_data.settings["FPS"])
        self._last_tick_time = time.perf_counter()
        self.dt: float = 0.0

        # Inicjalizacja funkcji API systemu Windows służące do zbiorczej aktualizacji z-index wielu okien w jednej operacji.
        self.user32 = ctypes.windll.user32
        HDWP = wintypes.HANDLE
        self.user32.BeginDeferWindowPos.argtypes = [ctypes.c_int]
        self.user32.BeginDeferWindowPos.restype = HDWP
        self.user32.DeferWindowPos.argtypes = [HDWP, wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
        self.user32.DeferWindowPos.restype = HDWP
        self.user32.EndDeferWindowPos.argtypes = [HDWP]
        self.user32.EndDeferWindowPos.restype = wintypes.BOOL

        # Debugowanie
        self.process_timer = debug_overlay.NamedStopwatch(update_rate_sec=1)
        self.debug_window = debug_overlay.DebugWindow()
        self.hitbox_overlay = debug_overlay.HitboxOverlay()
        self.debug_window.hide()
        self.hitbox_overlay.hide()
        self.update_debug_visibility()
        if self.shared_data.args.debug >= 2:
            self.debug_window.show()
            self.hitbox_overlay.show()

    def tick(self):
        self.process_timer.start("tick")
        # --- Obliczenie Delta Time ---
        now = time.perf_counter()
        self.dt = now - self._last_tick_time
        self._last_tick_time = now

        self.process_timer.start("hwnd update")
        if self.on_window_hwnd is None or not is_real_window(self.on_window_hwnd): # Jeżeli okno nie istnieje
            above_rwindow_hwnd, below_rwindow_hwnd = get_immediate_neighbors_above_and_below(self.hwnd_self, True, [obj.hwnd_self for obj in self.world_objects])
            logger.debug(f"[Pet] Set \"on_window_hwnd\" to {below_rwindow_hwnd} ({win32gui.GetWindowText(below_rwindow_hwnd)}) due to detection of non-existent window {self.on_window_hwnd}")
            self.on_window_hwnd = below_rwindow_hwnd
        else: # Jeżeli okno istnieje, ale na przykład zmieniło z-index
            above_rwindow_hwnd, below_rwindow_hwnd = get_immediate_neighbors_above_and_below(self.hwnd_self, True, [obj.hwnd_self for obj in self.world_objects] + [self.hwnd_self])
            if below_rwindow_hwnd != self.on_window_hwnd: # Zmień z-index zwierzątka tylko wtedy gdy `self.on_window_hwnd` zmieniło z-index
                above_window_hwnd, below_window_hwnd = get_immediate_neighbors_above_and_below(self.on_window_hwnd, False, [obj.hwnd_self for obj in self.world_objects] + [self.hwnd_self, self.on_window_hwnd])
                win32gui.SetWindowPos(self.hwnd_self, above_window_hwnd, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE)
                # logger.debug(f"[Pet] Changed pet z-index")
        self.process_timer.stop("hwnd update")

        self.process_timer.start("window rect update")
        # --- Pobieranie pozycji i wymiarów platformy ---
        window_rect: tuple[int, int, int, int] = win32gui.GetWindowRect(self.on_window_hwnd) # (x, y, x2, y2)
        # --- Obliczanie hitboxu platformy ---
        window_rect: XYXY_Rectangle = XYXY_Rectangle(window_rect[0], window_rect[1], window_rect[2], window_rect[1]) # platforma o wysokości 1 pixela (y = y2)
        if self.old_window_rect is None or self.old_on_window_hwnd != self.on_window_hwnd:
            self.old_window_rect = window_rect
        expanded_platform_rect: XYXY_Rectangle = XYXY_Rectangle(
            min(window_rect.x, self.old_window_rect.x),
            min(window_rect.y, self.old_window_rect.y),
            max(window_rect.x2, self.old_window_rect.x2),
            max(window_rect.y2, self.old_window_rect.y2),
        )
        self.process_timer.stop("window rect update")

        # --- Fizyka platformy ---
        platform_dx = window_rect.x - self.old_window_rect.x
        platform_dy = window_rect.y2 - self.old_window_rect.y2
        platform_vx = platform_dx / self.dt
        platform_vy = platform_dy / self.dt

        # --- Obliczanie fizyki (tarcia i grawitacji) ---
        if self.is_dragging == False:
            self.velocity[1] = self.velocity[1] + self.gravity * self.dt
            ax_drag = -self.drag_air_k * self.velocity[0] * abs(self.velocity[0]) / self.mass
            ay_drag = -self.drag_air_k * self.velocity[1] * abs(self.velocity[1]) / self.mass
            self.velocity[0] += ax_drag * self.dt
            if self.on_ground:
                if abs(self.velocity[0]) < self.min_vx_threshold:
                    self.velocity[0] = 0.0
                dv = self.mu_static * self.gravity * self.dt
                if dv >= abs(self.velocity[0]):
                    self.velocity[0] -= self.velocity[0]
                else:
                    self.velocity[0] -= (dv * (1 if self.velocity[0] > 0 else -1))
            self.velocity[1] += ay_drag * self.dt

        # System zadań i zachowań
        if self.on_ground or self.on_window:
            # Ustawianie zadania
            if time.perf_counter() - self.task_end_time > 0:
                # Ustawianie zadań priorytetowych
                screen_geo = QtWidgets.QApplication.primaryScreen().virtualGeometry()
                size = self.animations[self.current_animation].frameRect().size()
                if self.real_x < screen_geo.left() - size.width() // 2:
                    self.current_task = "Walking"
                    self.task_end_time = time.perf_counter() + random.randint(5, 10)
                    self.orientation = "right"
                    self.set_animation(f"{self.orientation}_walking.gif")
                elif self.real_x > screen_geo.right() - size.width() // 2:
                    self.current_task = "Walking"
                    self.task_end_time = time.perf_counter() + random.randint(5, 10)
                    self.orientation = "left"
                    self.set_animation(f"{self.orientation}_walking.gif")
                else:
                    # Szansa na zmiane kierunku
                    r = random.randint(0, 100)
                    if r <= 25:
                        self.orientation = "right" if self.orientation == "left" else "left"

                    # Ustawianie zadań nie priorytetowych
                    task = random.choices(self.tasks.names, self.tasks.weights)[0]
                    if task == "Standing":
                        self.current_task = "Standing"
                        self.task_end_time = time.perf_counter() + random.randint(5, 10)
                        self.set_animation(f"{self.orientation}.gif")
                    elif task == "Sleeping":
                        self.current_task = "Sleeping"
                        self.task_end_time = time.perf_counter() + random.randint(60, 120)
                        self.set_animation(f"{self.orientation}_sleeping.gif")
                    elif task == "Sitting":
                        self.current_task = "Sitting"
                        self.task_end_time = time.perf_counter() + random.randint(10, 20)
                        self.set_animation(f"{self.orientation}_sitting.gif")
                    elif task == "Walking":
                        self.current_task = "Walking"
                        self.task_end_time = time.perf_counter() + random.randint(5, 10)
                        self.set_animation(f"{self.orientation}_walking.gif")
                    else:
                        raise Exception("Error: No task was set. This should not happen!")

            # Wykonywanie zadania
            if self.current_task == "Walking":
                if self.orientation == "left":
                    self.real_x -= 50 * self.dt
                elif self.orientation == "right":
                    self.real_x += 50 * self.dt
        else:
            self.current_task = "Falling"
            self.task_end_time = time.perf_counter() + 0.1
            self.set_animation(f"{self.orientation}_falling.gif")

        # --- Zapisywanie starej pozycji zwierzątka ---
        self.old_window_rect = window_rect
        self.old_real_x, self.old_real_y = self.real_x, self.real_y
        self.old_on_window_hwnd = self.on_window_hwnd

        # --- Aktualizowanie wyświetlanej pozycji zwierzątka ---
        if self.is_dragging == False:
            self.real_x += self.velocity[0] * self.dt
            self.real_y += self.velocity[1] * self.dt

        # self.move(round(self.real_x), round(self.real_y))

        if self.is_dragging == False:
            # --- Obliczanie hitboxu stóp zwierzątka ---
            pet_foot_rect: XYWH_Rectangle = XYWH_Rectangle(
                self.real_x + self.foot_x,
                self.real_y + self.foot_y,
                self.real_x + self.foot_x + self.foot_width,
                self.real_y + self.foot_y
            )
            pet_foot_rect = XYWH_Rectangle(
                int(min(pet_foot_rect.x, pet_foot_rect.x + self.velocity[0] * self.dt)),
                int(min(pet_foot_rect.y, pet_foot_rect.y - self.velocity[1] * self.dt)),
                math.ceil(max(pet_foot_rect.width, pet_foot_rect.width + self.velocity[0] * self.dt)),
                math.ceil(max(pet_foot_rect.height, pet_foot_rect.height + self.velocity[1] * self.dt))
            )

            # --- Rysowanie hitboxów do debugowania ---
            rect_objects = list({(obj.debug_expanded_platform_rect.as_tuple, (100, 255, 0, 180)) for obj in self.world_objects})
            if self.hitbox_overlay is not None:
                self.hitbox_overlay.update_hitboxes(
                    [
                        (pet_foot_rect.as_tuple, (0, 255, 0, 180) if self.on_window else (255, 0, 0, 180)),
                        (expanded_platform_rect.as_tuple, (0, 255, 0, 180) if self.on_window else (255, 0, 0, 180))
                    ] + rect_objects,
                    [
                        # (self.animacje_hitbox[self.obecna_animacja].currentImage(), int(self.real_x), int(self.real_y))
                    ]
                )

            if CustomHitboxCollisions.check_rect_hitbox_collision(pet_foot_rect, expanded_platform_rect):
                if self.velocity[1] - platform_vy > 0:
                    self.velocity[1] = -(self.velocity[1] - platform_vy) * self.restitution
                    self.real_y = window_rect.y2 - self.foot_y
                    # self.move(round(self.real_x), round(self.real_y))
                if platform_vy < 0.0:
                    self.velocity[1] = platform_vy

                v_rel = self.velocity[0] - platform_vx
                max_dv_friction = self.mu_kinetic * self.gravity * self.dt
                impulse_gain = 0.25
                max_dv_impulse = abs(platform_vx) * impulse_gain
                max_dv = max(max_dv_friction, max_dv_impulse)
                static_threshold = self.mu_static * self.gravity * self.dt
                if abs(v_rel) <= static_threshold:
                    self.velocity[0] = platform_vx
                else:
                    dv = math.copysign(min(abs(v_rel), max_dv), v_rel)
                    new_v_rel = v_rel - dv
                    self.velocity[0] = platform_vx + new_v_rel

                self.on_window = True
            else:
                self.on_window = False

            # --- Fizyka ziemi ---
            if self.real_y >= self.taskbar_y - self.foot_y:
                self.real_y = self.taskbar_y - self.foot_y
                if self.velocity[1] > 0:
                    self.velocity[1] = -self.velocity[1] * self.restitution
                # self.move(round(self.real_x), round(self.real_y))
                self.on_ground = True
            else:
                self.on_ground = False
        else:
            self.on_window = False
            self.on_ground = False

        self.move(round(self.real_x), round(self.real_y))

        self.check_messages()

        self.process_timer.start("objects tick")
        self.process_timer.start("objects update hwnd")

        calculated_above_hwnds: dict[int, int | None] = {}
        ignored_hwnds = [obj.hwnd_self for obj in self.world_objects] + [self.hwnd_self]
        hdwp = self.user32.BeginDeferWindowPos(len(self.world_objects))
        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        for object in self.world_objects:
            # --- Pobieranie hwnd okna pod obiektem ---
            if object.on_window_hwnd is None or not win32gui.IsWindow(object.on_window_hwnd):
                object.on_window_hwnd = get_immediate_neighbors_above_and_below(object.hwnd_self, True, ignored_hwnds)[1]
                logger.debug(f"[Obj] Set new \"on_window_hwnd\" to {object.on_window_hwnd} ({win32gui.GetWindowText(object.on_window_hwnd)}) on object {object.hwnd_self}")

            if object.on_window_hwnd in calculated_above_hwnds:
                if calculated_above_hwnds[object.on_window_hwnd] is not None:
                    # if hdwp:
                    hdwp = self.user32.DeferWindowPos(hdwp, object.hwnd_self, calculated_above_hwnds[object.on_window_hwnd], 0, 0, 0, 0, flags)
                    # logger.debug(f"[Obj] Zmiana warstwy obiektu {object.hwnd_self}")
            else:
                # --- Ustawianie warstwy okna obiektem ---
                # logger.debug(f"[Obj] Sprawdzanie poprawnego z-index obiektu {object.hwnd_self}")
                above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(object.hwnd_self, True, ignored_hwnds)
                if below_hwnd == object.on_window_hwnd:
                    calculated_above_hwnds[object.on_window_hwnd] = None
                else:
                    above_hwnd, below_hwnd = get_immediate_neighbors_above_and_below(object.on_window_hwnd, False, ignored_hwnds)
                    calculated_above_hwnds[object.on_window_hwnd] = above_hwnd
                    # if hdwp:
                    hdwp = self.user32.DeferWindowPos(hdwp, object.hwnd_self, calculated_above_hwnds[object.on_window_hwnd], 0, 0, 0, 0, flags)
                    logger.debug(f"[Obj] Set new \"on_window_hwnd\" to {object.on_window_hwnd} ({win32gui.GetWindowText(object.on_window_hwnd)}) on object {object.hwnd_self}")
        self.process_timer.stop("objects update hwnd")

        self.process_timer.start("objects DeferWindowPos")
        self.user32.EndDeferWindowPos(hdwp)
        self.process_timer.stop("objects DeferWindowPos")

        self.process_timer.start("objects psychic ticks")
        window_rects: dict[int, tuple[int, int, int, int]] = {}
        for object in self.world_objects:
            # Pobieranie i zapisywanie rozmiarów okna `on_window_hwnd` danego obiektu, aby zmniejszyć liczbę wywołań `GetWindowRect`
            if object.on_window_hwnd not in window_rects:
                window_rects[object.on_window_hwnd] = win32gui.GetWindowRect(object.on_window_hwnd)
            object.tick(self.dt, window_rects[object.on_window_hwnd])
        self.space.step(self.dt)
        self.process_timer.stop("objects psychic ticks")

        self.process_timer.stop("objects tick")

        self.process_timer.stop("tick")

        # --- Aktualizacja panelu debugowego ---
        self.process_timer.add_time("real fps", self.dt)
        self.process_timer._update_average_time("SetWindowPos", ignore_error=True)
        if self.debug_window is not None:
            c = debug_overlay.Color
            stringifyColors = c.StringifyColors()
            c_name = c(200, 200, 200)
            c_int = c(0, 200, 0)
            self.debug_window.update_debug(
f'''{c_name}on_window_hwnd: {stringifyColors.stringify(self.on_window_hwnd)}{c_name} ({win32gui.GetWindowText(self.on_window_hwnd)})
{c_name}real_x: {stringifyColors.stringify(round(self.real_x, 1))}
{c_name}real_y: {stringifyColors.stringify(round(self.real_y, 1))}
{c_name}velocity_x: {stringifyColors.stringify(round(self.velocity[0] * self.dt, 1))}
{c_name}velocity_y: {stringifyColors.stringify(round(self.velocity[1] * self.dt, 1))}
{c_name}on_ground: {stringifyColors.stringify(self.on_ground)}
{c_name}on_window: {stringifyColors.stringify(self.on_window)}
{c_name}pet_foot_rect: {stringifyColors.stringify(pet_foot_rect) if "pet_foot_rect" in locals() else None}
{c_name}platform_rect: {stringifyColors.stringify(window_rect)}
{c_name}expanded_platform_rect: {stringifyColors.stringify(expanded_platform_rect)}
{c_name}platform_expand: {stringifyColors.stringify((expanded_platform_rect.x2 - window_rect.x2, expanded_platform_rect.y2 - window_rect.y2))}
{c_name}platform_velocity_x: {stringifyColors.stringify(round(platform_vx)) if "platform_vx" in locals() else None}
{c_name}platform_velocity_y": {stringifyColors.stringify(round(platform_vy)) if "platform_vy" in locals() else None}
{"".join([f"{c_name}{name}: {c_int}{debug_overlay.format_number(self.process_timer.get_avg_fps(name), f"{c(0, 150, 0)}'{c_int}")} {c(200, 255, 200)}FPS\n" for name in self.process_timer.get_timers()])}'''
            )

    def send_message(self, msg):
        if msg:
            logger.info(f"[Pet] Sent IPC: {msg}")
            self.conn.send(msg)

    def check_messages(self):
        '''Checks messages from other processes'''
        if self.conn.poll():
            msg = self.conn.recv()
            logger.info(f"[Pet] Received IPC: {msg}")
            if msg[0] == "spawn_object":
                img_path = os.path.join("Assets", "Objects", msg[1])
                if not os.path.exists(img_path):
                    logger.error("[Obj] File not found:", img_path)

                x, y = win32gui.GetCursorPos()
                obj = WorldObject(self.shared_data, self.world_objects, self.space, img_path, x, y)
                self.world_objects.append(obj)
                obj.show()
            elif msg[0] == "clear_all_objects":
                for obj in list(self.world_objects):
                    self.space.remove(obj.platform_body, obj.platform_shape)
                    self.space.remove(obj.body, obj.shape)
                    obj.deleteLater()
                    obj.close()
                self.world_objects.clear()
            elif msg[0] == "toggle_debug":
                self.update_debug_visibility()
            elif msg[0] == "show_pet":
                self.show()
            elif msg[0] == "hide_pet":
                self.hide()
            elif msg[0] == "teleport_pet":
                size = self.animations[self.current_animation].frameRect().size()
                pos = QtGui.QCursor.pos()
                self.velocity = [0, 0]
                self.real_x, self.real_y = pos.x() - size.width() // 2, pos.y() - size.height() // 2
                self.is_dragging = False
            else:
                logger.error(f"Unknown command: {msg}")

    def update_debug_visibility(self):
        '''Updates visibility of debug overlays'''
        if self.shared_data.settings["debug"]["active"] and self.shared_data.settings["debug"]["hitbox_overlay"]: self.hitbox_overlay.show()
        else: self.hitbox_overlay.hide()
        if self.shared_data.settings["debug"]["active"] and self.shared_data.settings["debug"]["debug_window"]: self.debug_window.show()
        else: self.debug_window.hide()

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

    def compute_launch_velocity(self, target_x: int, target_y: int) -> tuple[float, float]:
        '''Calculates velocity needed to reach target position'''
        start_x, start_y = self.real_x, self.real_y

        # Przesunięcie do celu
        dx = target_x - start_x
        dy = target_y - start_y
        dist = math.hypot(dx, dy)

        T = max(0.5, min(dist / 700.0, 2.5))

        g = self.gravity
        vx = dx / T
        vy = (dy - 0.5 * g * T ** 2) / T

        dt_sim = 0.016

        for _ in range(12):
            sim_x, sim_y = start_x, start_y
            sim_vx, sim_vy = vx, vy
            t = 0.0

            while t < T:
                sim_vy += g * dt_sim

                ax_drag = -self.drag_air_k * sim_vx * abs(sim_vx) / self.mass
                ay_drag = -self.drag_air_k * sim_vy * abs(sim_vy) / self.mass

                sim_vx += ax_drag * dt_sim
                sim_vy += ay_drag * dt_sim

                sim_x += sim_vx * dt_sim
                sim_y += sim_vy * dt_sim

                t += dt_sim

            error_x = target_x - sim_x
            error_y = target_y - sim_y

            if abs(error_x) < 2 and abs(error_y) < 2:
                break

            vx += (error_x / T) * 1.1
            vy += (error_y / T) * 1.1

        return (vx, vy)

    def keyPressEvent(self, event): # Tymczasowa funkcja do debugowania i testowania
        '''Temporary function for debugging and testing'''
        if event.key() == QtCore.Qt.Key.Key_Space:
            self.real_x, self.real_y = 800 , 200
            self.velocity: list = [400.0, -800.0]
        elif event.key() == QtCore.Qt.Key.Key_1:
            self.velocity = list(self.compute_launch_velocity(0, self.taskbar_y))
        elif event.key() == QtCore.Qt.Key.Key_Up:
            self.on_window_hwnd = get_immediate_neighbors_above_and_below(self.shared_data.pet["hwnd"], True, [obj.hwnd_self for obj in self.world_objects])[0]
            logger.debug(f"[Pet] Set \"on_window_hwnd\" to {self.on_window_hwnd} ({win32gui.GetWindowText(self.on_window_hwnd)})")
        elif event.key() == QtCore.Qt.Key.Key_Down:
            self.on_window_hwnd = get_immediate_neighbors_above_and_below(self.shared_data.pet["hwnd"], True, [obj.hwnd_self for obj in self.world_objects] + [self.on_window_hwnd])[1]
            logger.debug(f"[Pet] Set \"on_window_hwnd\" to {self.on_window_hwnd} ({win32gui.GetWindowText(self.on_window_hwnd)})")
        else:
            super().keyPressEvent(event)

    def set_animation(self, animation):
        '''Sets and starts a new animation'''
        if animation != self.current_animation:
            # Zatrzymanie poprzednich animacji
            if self.current_animation:
                self.animations[self.current_animation].stop()
                self.hitbox_animations[self.current_animation].stop()

            #Ustawienie i start nowej animacji
            self.pet_label.setMovie(self.animations[animation])
            self.animations[animation].start()
            # Ustawienie i start nowej maski hitboxa
            self.hitbox_animations[animation].start()
            self.hitbox_animations[animation].jumpToFrame(0)

            self.pet_label.resize(self.animations[animation].frameRect().size())
            self.resize(self.animations[animation].frameRect().size())
            self.current_animation = animation

    def mousePressEvent(self, event):
        self.is_dragging = True
        self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        self.velocity = [0, 0]

    def mouseMoveEvent(self, event):
        pos = event.globalPosition().toPoint() - self._drag_pos
        self.real_x, self.real_y = pos.x(), pos.y()

    def mouseReleaseEvent(self, event):
        self.is_dragging = False
        self.velocity = [
            (self.real_x - self.old_real_x) / self.dt,
            (self.real_y - self.old_real_y) / self.dt
        ]

def run_app(conn, shared_data, log_queue):
    '''Entry point for the pet process'''
    global logger
    logger = setup_process_logger("pet", log_queue)
    logger.info("Starting the PET process...")

    app = QtWidgets.QApplication(sys.argv)
    pet = PetWidget(conn, shared_data)
    pet.show()

    sys.exit(app.exec())
