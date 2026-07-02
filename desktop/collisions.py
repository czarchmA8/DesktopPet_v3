from PySide6.QtCore import QRect
from enum import IntEnum, auto
from dataclasses import dataclass

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
