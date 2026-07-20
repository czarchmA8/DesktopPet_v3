from dataclasses import dataclass
import math
from pathlib import Path
import json
import logging

import win32gui, win32con
import ctypes
from ctypes import wintypes
from PySide6 import QtWidgets, QtCore, QtGui
from Box2D import (
    b2Body,
    b2World,
    b2EdgeShape,
    b2PolygonShape,
    b2CircleShape,
    b2FixtureDef,
    b2ContactListener,
)

from windows_layer import get_immediate_neighbors_above_and_below as get_immediate_neighbors_above_and_below
from logger_setup import setup_process_logger
from desktop.physics_utils import (
    XYXY_Rectangle, CollisionTypes, 
    px_to_m, px_to_m_vec, m_to_px_vec, 
    polygon_area, simplify_convex_polygon,
    DEFAULT_FRICTION, DEFAULT_ELASTICITY, DEFAULT_MASS, DEFAULT_ANGULAR_DAMPING, DEFAULT_LINEAR_DAMPING,
    HitboxShapes,
)
from dashboard.objects_editor import generate_hull_vertices

logger: logging.Logger = logging.getLogger(__name__)

class PlatformContactListener(b2ContactListener):
    '''
    Handles collision filtering for one-way platforms and window-specific interactions.
    It ensures objects can pass through platforms from below
    and only collide with platforms sharing the same window handle (hwnd)
    '''

    def PreSolve(self, contact, oldManifold) -> None:
        fixture_a = contact.fixtureA
        fixture_b = contact.fixtureB
        data_a = fixture_a.userData or {}
        data_b = fixture_b.userData or {}

        if data_a.get("type") == CollisionTypes.OBJECT and data_b.get("type") == CollisionTypes.PLATFORM:
            object_data, platform_data = data_a, data_b
            normal_sign = 1
        elif data_b.get("type") == CollisionTypes.OBJECT and data_a.get("type") == CollisionTypes.PLATFORM:
            object_data, platform_data = data_b, data_a
            normal_sign = -1
        else:
            return

        # Obiekty mogą przelatywać od dołu do góry przez platformę
        world_manifold = contact.worldManifold
        normal_y = world_manifold.normal.y * normal_sign
        if normal_y < 0:
            contact.enabled = False
            return

        # Obiekt koliduje wyłącznie z daną platformą (tym samym oknem)
        if object_data.get("hwnd") != platform_data.get("hwnd"):
            contact.enabled = False

@dataclass
class Platform:
    body: b2Body
    fixture: None

class WorldObject(QtWidgets.QWidget):
    '''Interactive physics object'''
    def __init__(
        self,
        shared_data,
        world_objects: list["WorldObject"],
        space: b2World,
        image_path: Path,
        start_x: int,
        start_y: int,
        mass: float | None = None,
        elasticity: float | None = None,
        friction: float | None = None,
        angular_damping: float | None = None,
        linear_damping: float | None = None,
        shape: str | None = None,
        vertices: list[tuple[float, float] | list[float]] | None = None,
        circle_center: tuple[float, float] | None = None,
        circle_radius: float | None = None,
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
        raw_vertices: list[tuple[float, float] | list[float]] | list[tuple[float, float]] | list[list[float]] = []
        if object_settings_path.exists():
            with open(object_settings_path, "r", encoding="utf-8") as f:
                object_settings: dict = json.load(f)

            shape = shape if shape else object_settings["shape"]
            mass = mass if mass else object_settings["mass"]
            elasticity = elasticity if elasticity else object_settings["elasticity"]
            friction = friction if friction else object_settings["friction"]
            angular_damping = angular_damping if angular_damping else object_settings["angular_damping"]
            linear_damping = linear_damping if linear_damping else object_settings["linear_damping"]

            if shape == HitboxShapes.POLYGON:
                raw_vertices = vertices if vertices else object_settings["vertices"]
            elif shape == HitboxShapes.CIRCLE:
                circle_center = circle_center if circle_center else object_settings["center"]
                circle_radius = circle_radius if circle_radius else object_settings["radius"]
            else:
                raise Exception(f'Unknown hitbox shape "{shape}"')
        else:
            # Each object should have a settings file, but I decided to add default values anyway
            shape = shape if shape else HitboxShapes.POLYGON
            mass = mass if mass else DEFAULT_MASS
            elasticity = elasticity if elasticity else DEFAULT_ELASTICITY
            friction = friction if friction else DEFAULT_FRICTION
            angular_damping = angular_damping if angular_damping else DEFAULT_ANGULAR_DAMPING
            linear_damping = linear_damping if linear_damping else DEFAULT_LINEAR_DAMPING
            
            settings_to_save = {
                "shape": shape,
                "mass": mass,
                "elasticity": elasticity,
                "friction": friction,
                "angular_damping": angular_damping,
                "linear_damping": linear_damping,
            }
            if shape == HitboxShapes.POLYGON:
                raw_vertices = vertices if vertices else generate_hull_vertices(self.original_pixmap)
                settings_to_save = settings_to_save | {
                    "vertices": raw_vertices,
                }
            elif shape == HitboxShapes.CIRCLE:
                circle_center = circle_center if circle_center else (0.0, 0.0)
                circle_radius = circle_radius if circle_radius else self.original_pixmap.width() // 2
                settings_to_save = settings_to_save | {
                    "center": list(circle_center),
                    "radius": circle_radius,
                }
            else:
                raise Exception(f'Unknown hitbox shape "{shape}"')
            with open(object_settings_path, "w", encoding="utf-8") as f:
                json.dump(settings_to_save, f, ensure_ascii=False)
            logger.debug(f"A new file \"{object_settings_path.name}\" has been created for the object")

        self.hwnd_self = int(self.winId())

        # --- SPACE fizyki ---
        self.space: b2World = space
        self.on_window_hwnd: int | None = None

        # --- Ciało fizyczne ---
        if shape == HitboxShapes.POLYGON:
            vertices_normalized: list[tuple[float, float]] = [(v[0], v[1]) for v in raw_vertices]
            vertices_m_full = [(px_to_m(v[0]), px_to_m(v[1])) for v in vertices_normalized]
            vertices_m = simplify_convex_polygon(vertices_m_full, max_vertices=16)
            area_m2 = polygon_area(vertices_m)
            density = mass / area_m2 if area_m2 > 1e-9 else 1.0
            fixture_shape = b2PolygonShape(vertices=vertices_m)
        elif shape == HitboxShapes.CIRCLE:
            assert circle_radius is not None, "`circle_radius` cannot be equal to None"
            assert circle_center is not None, "`circle_center` cannot be equal to None"
            radius_m = px_to_m(circle_radius)
            center_m = px_to_m_vec(circle_center[0], circle_center[1])
            area_m2 = math.pi * radius_m ** 2
            density = mass / area_m2 if area_m2 > 1e-9 else 1.0
            fixture_shape = b2CircleShape(pos=center_m, radius=radius_m)
        else:
            raise Exception(f'Unknown hitbox shape "{shape}"')

        object_fixture_def = b2FixtureDef(
            shape=fixture_shape,
            density=density,
            friction=friction,
            restitution=elasticity,
            userData={"type": CollisionTypes.OBJECT, "hwnd": None},
        )
        self.body = self.space.CreateDynamicBody(
            position=px_to_m_vec(start_x, start_y),
            fixtures=object_fixture_def,
            angularDamping=angular_damping,
            linearDamping=linear_damping,
        )
        self.fixture = self.body.fixtures[0]

        # --- Mouse body + joint (do przeciągania) ---
        self.mouse_body = self.space.CreateKinematicBody(position=(0, 0))

        self.mouse_joint = None
        self.is_dragging: bool = False

        self.pos_x: float = float(start_x)
        self.pos_y: float = float(start_y)
        self.angle, self.old_angle = 0.0, 0.0

    def tick(self):
        '''Updates physics and visuals for world object'''
        self.pos_x, self.pos_y = m_to_px_vec(self.body.position)
        self.old_angle = self.angle
        self.angle = math.degrees(self.body.angle)
        self.update_visuals()

        # Usuwanie obiektu jeżeli jest poza ekranami
        screen_geo = QtWidgets.QApplication.primaryScreen().virtualGeometry()
        if self.pos_x < screen_geo.left() - self.w or self.pos_x > screen_geo.right() + self.w or self.pos_y > screen_geo.bottom() + self.h:
            logger.info(f"Removed WorldObject: {self.hwnd_self}")
            self.world_objects.remove(self)
            self.space.DestroyBody(self.body)
            self.close()
            self.deleteLater()

    def update_visuals(self) -> None:
        '''Updates visual position and rotation'''
        if self.pos_x is None or self.pos_y is None:
            return
        if math.isnan(self.pos_x) or math.isnan(self.pos_y):
            return

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
            new_pos = px_to_m_vec(m_pos.x(), m_pos.y())

            self.mouse_body.position = new_pos

            self.mouse_joint = self.space.CreateMouseJoint(
                bodyA=self.mouse_body,
                bodyB=self.body,
                target=new_pos,
                maxForce=1000.0 * self.body.mass,
                frequencyHz=5.0,
                dampingRatio=0.7,
            )

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
        target = px_to_m_vec(m_pos.x(), m_pos.y())
        self.mouse_body.position = target
        if self.mouse_joint is not None:
            self.mouse_joint.target = target

    def mouseReleaseEvent(self, event) -> None:
        '''Handles mouse release after drag'''
        if event.button() == QtCore.Qt.MouseButton.LeftButton and self.is_dragging:
            self.is_dragging = False

            if self.mouse_joint is not None:
                try:
                    self.space.DestroyJoint(self.mouse_joint)
                except Exception:
                    pass
                self.mouse_joint = None

            try:
                self.body.awake = True
            except Exception:
                pass

            self.pos_x, self.pos_y = m_to_px_vec(self.body.position)
            self.angle = math.degrees(self.body.angle)

class WorldObjectsManager:
    def __init__(self, shared_data, log_queue) -> None:
        self.shared_data = shared_data

        global logger
        logger = setup_process_logger("world_objects", log_queue)
        logger.info("Creating the WorldObjectsManager...")

        self.world_objects: list[WorldObject] = []

        # Fizyka obiektów
        self.space = b2World(gravity=px_to_m_vec(0.0, 2000.0), doSleep=True)
        self.contact_listener = PlatformContactListener()
        self.space.contactListener = self.contact_listener

        # Platformy
        self.debug_platform_rects: dict[int, XYXY_Rectangle] = {}
        self.old_window_rects: dict[int, XYXY_Rectangle] = {}
        self.platforms: dict[int, Platform] = {}
        self.platform_friction: float = 0.5
        self.platform_elasticity: float = 0.5

        # Podłoga ekranu
        screen_geo = QtWidgets.QApplication.primaryScreen().availableGeometry()
        floor_fixture_def = b2FixtureDef(
            shape=b2EdgeShape(vertices=[
                px_to_m_vec(-10000, screen_geo.bottom()),
                px_to_m_vec(10000, screen_geo.bottom()),
            ]),
            friction=1.0,
            restitution=0.5,
        )
        self.floor_body = self.space.CreateStaticBody(fixtures=floor_fixture_def)

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
        """Updates z-index, physics and visuals for world objects"""
        calculated_above_hwnds: dict[int, int | None] = {}
        ignored_hwnds = [obj.hwnd_self for obj in self.world_objects] + [pet_hwnd]
        hdwp = self.user32.BeginDeferWindowPos(len(self.world_objects))
        flags = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        for object in self.world_objects:
            # --- Pobieranie hwnd okna pod obiektem ---
            if object.on_window_hwnd is None or not win32gui.IsWindow(object.on_window_hwnd):
                object.on_window_hwnd = get_immediate_neighbors_above_and_below(object.hwnd_self, True, ignored_hwnds)[1]
                object.fixture.userData["hwnd"] = object.on_window_hwnd
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

        window_rects: dict[int, XYXY_Rectangle] = {}
        self.debug_platform_rects.clear()
        for object in self.world_objects:
            # Pobieranie i zapisywanie rozmiarów okna `on_window_hwnd` danego obiektu, aby zmniejszyć liczbę wywołań `GetWindowRect`
            on_window_hwnd = object.on_window_hwnd
            assert on_window_hwnd is not None

            if on_window_hwnd not in window_rects:
                window_XYXY_Rect: tuple[int, int, int, int] = win32gui.GetWindowRect(on_window_hwnd)
                window_rects[on_window_hwnd] = XYXY_Rectangle(
                    window_XYXY_Rect[0],
                    window_XYXY_Rect[1],
                    window_XYXY_Rect[2],
                    window_XYXY_Rect[3],
                )
                window_rect: XYXY_Rectangle = window_rects[on_window_hwnd]

                if on_window_hwnd not in self.old_window_rects:
                    self.old_window_rects[on_window_hwnd] = window_rect
                old_window_rect: XYXY_Rectangle = self.old_window_rects[on_window_hwnd]

                expanded_platform_rect: XYXY_Rectangle = XYXY_Rectangle(
                    min(window_rect.x, old_window_rect.x),
                    min(window_rect.y, old_window_rect.y),
                    max(window_rect.x2, old_window_rect.x2),
                    max(window_rect.y, old_window_rect.y),
                )
                self.debug_platform_rects[on_window_hwnd] = expanded_platform_rect

                platform = self.platforms.get(on_window_hwnd)
                if platform is None:
                    body: b2Body = self.space.CreateKinematicBody(position=px_to_m_vec(0, -1000))
                    platform = Platform(body=body, fixture=None)
                    self.platforms[on_window_hwnd] = platform
                    logger.debug(f"Created a new common platform for window {on_window_hwnd}")
                platform_body: b2Body = platform.body

                vx = (window_rect.x - old_window_rect.x) / dt
                vy = (window_rect.y - old_window_rect.y) / dt
                platform_body.linearVelocity = px_to_m_vec(vx, vy)

                # Zamiana wartości potrzebne do poprawnego funkcjonowania fizyki
                width, height = (abs(expanded_platform_rect.x2 - expanded_platform_rect.x), abs(expanded_platform_rect.y2 - expanded_platform_rect.y))
                x, y = (expanded_platform_rect.x + width // 2, expanded_platform_rect.y + height // 2)

                platform_body.position = px_to_m_vec(x, y)

                # Aktualizacja rozmiaru i pozycji platformy
                if platform.fixture is not None:
                    platform_body.DestroyFixture(platform.fixture)
                half_width = px_to_m(max(width, 1) / 2)
                half_height = px_to_m(max(height, 1) / 2)
                new_platform_fixture_def = b2FixtureDef(
                    shape=b2PolygonShape(box=(half_width, half_height)),
                    friction=self.platform_friction,
                    restitution=self.platform_elasticity,
                    userData={"type": CollisionTypes.PLATFORM, "hwnd": on_window_hwnd},
                )
                platform.fixture = platform_body.CreateFixture(new_platform_fixture_def)
            object.tick()
        self.old_window_rects = window_rects

        # Usuwanie platform okien, na których nie stoi już żaden obiekt
        for hwnd in list(self.platforms.keys()):
            if hwnd not in window_rects:
                self.space.DestroyBody(self.platforms[hwnd].body)
                del self.platforms[hwnd]
                self.old_window_rects.pop(hwnd, None)

        self.space.Step(dt, 8, 3)
        self.space.ClearForces()

    def spawn_object(self, path: str) -> None:
        '''Creates an object from an image with the given path'''
        img_path = Path("Assets") / "Objects" / path
        if not img_path.exists():
            logger.error("[Obj] File not found:", img_path)

        x, y = win32gui.GetCursorPos()
        obj = WorldObject(self.shared_data, self.world_objects, self.space, img_path, x, y)
        self.world_objects.append(obj)
        obj.show()

    def clear_all_objects(self) -> None:
        '''Removes all world objects'''
        for obj in list(self.world_objects):
            self.space.DestroyBody(obj.body)
            obj.deleteLater()
            obj.close()
        self.world_objects.clear()

        for platform in self.platforms.values():
            self.space.DestroyBody(platform.body)
        self.platforms.clear()
        self.old_window_rects.clear()
