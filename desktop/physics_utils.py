from PySide6.QtCore import QRect
from enum import IntEnum, auto
from dataclasses import dataclass
from Box2D import b2Vec2

@dataclass
class XYXY_Rectangle:
    '''Rectangle defined by (x, y, x2, y2) coordinates'''
    x: int | float
    y: int | float
    x2: int | float
    y2: int | float

    @property
    def as_tuple(self) -> tuple[int | float, int | float, int | float, int | float]:
        """Returns rectangle as a clean tuple (x, y, x2, y2)"""
        return (self.x, self.y, self.x2, self.y2)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.x2
        yield self.y2

    def __getitem__(self, index):
        return self.as_tuple[index]

@dataclass
class XYWH_Rectangle:
    '''Rectangle defined by (x, y, width, height)'''
    x: int | float
    y: int | float
    width: int | float
    height: int | float

    @property
    def as_tuple(self) -> tuple[int | float, int | float, int | float, int | float]:
        """Returns rectangle as a clean tuple (x, y, width, height)"""
        return (self.x, self.y, self.width, self.height)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.width
        yield self.height

    def __getitem__(self, index):
        return self.as_tuple[index]

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
        rect1 = QRect(pos1[0], pos1[1], img1.width(), img1.height())
        rect2 = QRect(pos2[0], pos2[1], img2.width(), img2.height())

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

PPM: float = 100.0 # PPM (pixels-per-meter)

def px_to_m(value: float) -> float:
    '''Converts a scalar value from pixels to meters'''
    return value / PPM

def m_to_px(value: float) -> float:
    '''Converts a scalar value from meters to pixels'''
    return value * PPM

def px_to_m_vec(x: float, y: float) -> b2Vec2:
    '''Converts a pixel-space (x, y) pair into a Box2D meter-space vector'''
    return b2Vec2(x / PPM, y / PPM)

def m_to_px_vec(vec) -> tuple[float, float]:
    '''Converts a Box2D meter-space vector into a pixel-space (x, y) tuple'''
    return (vec.x * PPM, vec.y * PPM)

def polygon_area(vertices: list[tuple[float, float]]) -> float:
    '''Returns the area of a polygon (shoelace formula), used to derive density from a target mass'''
    area = 0.0
    n = len(vertices)
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0

def simplify_convex_polygon(vertices: list[tuple[float, float]], max_vertices: int = 16) -> list[tuple[float, float]]:
    '''
    Reduces a convex polygon's vertex count to fit Box2D's b2_maxPolygonVertices limit.
    Repeatedly drops the vertex whose removal loses the least area (Visvalingam-Whyatt style).
    Since the remaining points stay in their original cyclic order, the result is still convex
    (a cyclically-ordered subset of a convex point set is itself convex) - it's just a smaller polygon.
    '''
    verts = list(vertices)

    def triangle_area(a, b, c) -> float:
        return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2.0

    while len(verts) > max_vertices:
        n = len(verts)
        areas = [triangle_area(verts[i - 1], verts[i], verts[(i + 1) % n]) for i in range(n)]
        idx_min = min(range(n), key=lambda i: areas[i])
        del verts[idx_min]
    return verts
