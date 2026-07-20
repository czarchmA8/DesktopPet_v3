import json
import math
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF, Signal, QTimer, QCoreApplication
from PySide6.QtGui import (
    QAction, QBrush, QColor,
    QCursor, QImage,
    QKeySequence, QPainter, QPen,
    QPixmap, QPolygonF, QIcon
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFileDialog, QLabel, QMainWindow,
    QMessageBox, QSpinBox, QStatusBar,
    QToolBar, QWidget, QPushButton,
    QHBoxLayout, QStackedWidget
)

from dashboard.translator import Translator
from desktop.physics_utils import (
    HitboxShapes, MAX_POLYGON_VERTICES,
    DEFAULT_MASS, DEFAULT_ELASTICITY, DEFAULT_FRICTION, DEFAULT_ANGULAR_DAMPING, DEFAULT_LINEAR_DAMPING,
)

MIN_ZOOM: float = 0.05
MAX_ZOOM: float = 256.0
GRID_MIN_ZOOM: float = 6.0 # from what zoom level to draw the pixel grid
MAX_HISTORY: int = 100

POINT_RADIUS: int = 5 # radius of the drawn point on the screen (px)
POINT_HIT_RADIUS: int = 9 # tolerance for grabbing a point with the mouse (screen px)

def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    '''Computes the convex hull of a set of 2D points'''
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    return lower[:-1] + upper[:-1]

def _simplify_hull_by_tolerance(hull: list[tuple[float, float]], tolerance: float) -> list[tuple[float, float]]:
    '''Drops hull vertices that lie within `tolerance` distance of the segment formed by their neighbors'''
    if tolerance <= 0 or len(hull) <= 3:
        return hull

    def point_segment_distance(p, a, b) -> float:
        ax, ay = a
        bx, by = b
        px, py = p
        dx, dy = bx - ax, by - ay
        length_sq = dx * dx + dy * dy
        if length_sq == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
        proj_x, proj_y = ax + t * dx, ay + t * dy
        return math.hypot(px - proj_x, py - proj_y)

    result = list(hull)
    changed = True
    while changed and len(result) > 3:
        changed = False
        n = len(result)
        for i in range(n):
            a = result[i - 1]
            b = result[i]
            c = result[(i + 1) % n]
            if point_segment_distance(b, a, c) <= tolerance:
                del result[i]
                changed = True
                break
    return result

def generate_hull_vertices(pixmap: QPixmap, alpha_threshold: int = 20, tolerance: float = 0.0) -> list[tuple[float, float]] | list[list[float]]:
    """Generates convex hull vertices based on the image's transparency."""
    image = pixmap.toImage()
    width, height = image.width(), image.height()
    if width == 0 or height == 0:
        raise Exception("The image is too small to generate a hitbox")

    img = image.convertToFormat(QImage.Format.Format_RGBA8888)
    buf = img.constBits()
    arr = np.frombuffer(buf, dtype=np.uint8, count=height * img.bytesPerLine())
    arr = arr.reshape((height, img.bytesPerLine()))[:, : width * 4].reshape((height, width, 4))
    alpha = arr[:, :, 3]
    ys, xs = np.nonzero(alpha > alpha_threshold)

    w2, h2 = width / 2.0, height / 2.0
    if xs.size == 0:
        return [(-w2, -h2), (w2, -h2), (w2, h2), (-w2, h2)]

    xs = xs.astype(np.float64)
    ys = ys.astype(np.float64)
    corner_dx = np.array([0.0, 1.0, 1.0, 0.0])
    corner_dy = np.array([0.0, 0.0, 1.0, 1.0])
    px = (xs[:, None] + corner_dx[None, :] - w2).ravel()
    py = (ys[:, None] + corner_dy[None, :] - h2).ravel()
    points: list[tuple[float, float]] = list(zip(px.tolist(), py.tolist()))

    hull = _convex_hull(points)
    hull = _simplify_hull_by_tolerance(hull, tolerance)
    return [(float(p[0]), float(p[1])) for p in hull]

class HitboxCanvas(QWidget):
    """A widget responsible for displaying the image and editing the hitbox polygon."""

    statusChanged = Signal(str)
    verticesChanged = Signal(list)
    circleChanged = Signal(tuple)
    shapeChanged = Signal(str)
    translate = QCoreApplication.translate

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(300, 300)

        self.translator = translator
        if self.translator is not None:
            self.translator.tr(lambda: self.update())

        self.pixmap: QPixmap | None = None
        self.image: QImage | None = None
        self.img_w = 0
        self.img_h = 0

        self.vertices: list[QPointF] = []

        self.shape: str = HitboxShapes.POLYGON
        self.circle_center: QPointF = QPointF(0.0, 0.0)
        self.circle_radius: float = 0.0

        self.zoom = 1.0
        self.pan = QPointF(0.0, 0.0)

        self.show_grid = True
        self.alpha_threshold = 20
        self.hull_tolerance = 0.0

        self.hover_index: int | None = None
        self.dragging_index: int | None = None
        self.selected_index: int | None = None
        self.dragging_circle_center: bool = False
        self.dragging_circle_radius: bool = False
        self.hover_circle_center: bool = False
        self.hover_circle_radius: bool = False
        self.panning = False
        self._last_mouse = QPointF()
        self._space_held = False

        # Each undo/redo entry is a full geometry snapshot (see _snapshot),
        # so switching shapes and editing either one are both undoable.
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []

    # ------------------------------------------------------------------ #
    # Coordinate conversions
    # ------------------------------------------------------------------ #
    def image_to_screen(self, p: QPointF) -> QPointF:
        return QPointF(
            self.pan.x() + p.x() * self.zoom,
            self.pan.y() + p.y() * self.zoom,
        )

    def screen_to_image(self, p: QPointF) -> QPointF:
        return QPointF(
            (p.x() - self.pan.x()) / self.zoom,
            (p.y() - self.pan.y()) / self.zoom,
        )

    def pixel_index_at(self, image_pt: QPointF) -> tuple[int, int] | None:
        """Returns the pixel index (px, py) of the image under a given point in image space."""
        if not self.pixmap:
            return None
        px = int((image_pt.x() + self.img_w / 2) // 1)
        py = int((image_pt.y() + self.img_h / 2) // 1)
        if 0 <= px < self.img_w and 0 <= py < self.img_h:
            return px, py
        return None

    def snap_point_to_pixel_grid(self, p: QPointF) -> QPointF:
        """
        Enforces the point's position on the pixel edge grid
        (the same grid used by generate_hull_vertices: integer coordinates in x - w/2, y - h/2 space)
        AND constrains it to the image boundaries.
        Always called - in this editor, points cannot be outside the grid or the image.
        """
        if not self.pixmap:
            return p
        w2, h2 = self.img_w / 2, self.img_h / 2
        gx = round(p.x() + w2) - w2
        gy = round(p.y() + h2) - h2
        gx = max(-w2, min(w2, gx))
        gy = max(-h2, min(h2, gy))
        return QPointF(gx, gy)

    # ------------------------------------------------------------------ #
    # Zarządzanie obrazkiem / wierzchołkami
    # ------------------------------------------------------------------ #
    def set_image(self, pixmap: QPixmap, skip_default_hull: bool = False) -> None:
        """Loads a new image"""
        self.pixmap = pixmap
        self.image = pixmap.toImage()
        self.img_w = pixmap.width()
        self.img_h = pixmap.height()
        self._undo_stack.clear()
        self._redo_stack.clear()

        self.shape = HitboxShapes.POLYGON
        self.circle_center = QPointF(0.0, 0.0)
        self.circle_radius = pixmap.width() // 2
        self.shapeChanged.emit(self.shape)

        if skip_default_hull:
            self.vertices = []
            self.selected_index = None
        else:
            self.recompute_default_hull(push_undo=False)
        QTimer.singleShot(0, self.fit_to_view)
        self.update()

    def recompute_default_hull(self, push_undo: bool = True) -> None:
        if not self.pixmap:
            return
        if push_undo:
            self.push_history()
        hull = generate_hull_vertices(self.pixmap, self.alpha_threshold, self.hull_tolerance)
        self.shape = HitboxShapes.POLYGON
        self.vertices = [self.snap_point_to_pixel_grid(QPointF(x, y)) for x, y in hull]
        self.selected_index = None
        self.shapeChanged.emit(self.shape)
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    def reset_bounding_box(self) -> None:
        if not self.pixmap:
            return
        self.push_history()
        w2, h2 = self.img_w / 2, self.img_h / 2
        self.shape = HitboxShapes.POLYGON
        self.vertices = [QPointF(-w2, -h2), QPointF(w2, -h2), QPointF(w2, h2), QPointF(-w2, h2)]
        self.selected_index = None
        self.shapeChanged.emit(self.shape)
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    def get_vertices(self) -> list[tuple[float, float]]:
        return [(p.x(), p.y()) for p in self.vertices]

    def set_vertices(self, vertices: list[tuple[float, float]]) -> None:
        self.push_history()
        self.vertices = [self.snap_point_to_pixel_grid(QPointF(x, y)) for x, y in vertices]
        self.selected_index = None
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    def get_circle(self) -> tuple[float, float, float]:
        """Returns the circle hitbox as (center_x, center_y, radius) in image space."""
        return (self.circle_center.x(), self.circle_center.y(), self.circle_radius)

    def set_circle(self, center: tuple[float, float], radius: float, push_undo: bool = True) -> None:
        if push_undo:
            self.push_history()
        self.circle_center = self.snap_point_to_pixel_grid(QPointF(center[0], center[1]))
        self.circle_radius = max(0.5, radius)
        self.circleChanged.emit(self.get_circle())
        self.update()

    def set_shape(self, shape: str) -> None:
        """Switches the hitbox kind. Geometries stay in memory,
        so switching back and forth doesn't lose the polygon or circle you edited."""
        if shape == self.shape:
            return
        self.push_history()
        self.shape = shape
        if self.shape == HitboxShapes.POLYGON and len(self.vertices) == 0:
            self.recompute_default_hull(push_undo=False)
        elif self.shape == HitboxShapes.CIRCLE and self.circle_radius <= 0:
            assert self.pixmap, "self.pixmap must exist!"
            self.circle_radius = self.pixmap.width() // 2
        self.selected_index = None
        self.dragging_circle_center = False
        self.dragging_circle_radius = False
        self.shapeChanged.emit(self.shape)
        self.update()

    def fit_to_view(self) -> None:
        if not self.pixmap or self.width() <= 1 or self.height() <= 1:
            return
        margin = 0.9
        zx = (self.width() / self.img_w) * margin
        zy = (self.height() / self.img_h) * margin
        self.zoom = max(MIN_ZOOM, min(MAX_ZOOM, min(zx, zy)))
        center = QPointF(self.width() / 2, self.height() / 2)
        self.pan = center
        self.update()
        self._emit_status()

    # ------------------------------------------------------------------ #
    # History (undo/redo)
    # ------------------------------------------------------------------ #
    def _snapshot(self) -> dict:
        """Captures the full editable geometry state (both shape kinds) for undo/redo."""
        return {
            "shape": self.shape,
            "vertices": self.get_vertices(),
            "circle": self.get_circle(),
        }

    def _restore(self, snapshot: dict) -> None:
        self.shape = snapshot["shape"]
        self.vertices = [QPointF(x, y) for x, y in snapshot["vertices"]]
        cx, cy, r = snapshot["circle"]
        self.circle_center = QPointF(cx, cy)
        self.circle_radius = r
        self.selected_index = None
        self.dragging_circle_center = False
        self.dragging_circle_radius = False
        self.shapeChanged.emit(self.shape)
        self.verticesChanged.emit(self.get_vertices())
        self.circleChanged.emit(self.get_circle())
        self.update()

    def push_history(self) -> None:
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(40, 40, 44))

        if not self.pixmap:
            painter.setPen(QColor(180, 180, 180))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.translate("HitboxCanvas", "Open an image: Ctrl+O", None))
            painter.end()
            return

        # Image
        top_left = self.image_to_screen(QPointF(-self.img_w / 2, -self.img_h / 2))
        dest_rect = QRectF(top_left, QSizeF(self.img_w * self.zoom, self.img_h * self.zoom))
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self.zoom < 4.0)
        painter.drawPixmap(dest_rect, self.pixmap, QRectF(self.pixmap.rect()))

        # Pixel grid
        if self.show_grid and self.zoom >= GRID_MIN_ZOOM:
            self._draw_pixel_grid(painter)

        # Highlighting the pixel under the cursor
        hover_pixel = self._hover_pixel
        if hover_pixel is not None and self.zoom >= GRID_MIN_ZOOM:
            self._draw_hovered_pixel(painter, hover_pixel)

        # Hitbox
        if self.shape == HitboxShapes.CIRCLE:
            self._draw_circle_hitbox(painter)
        elif self.vertices:
            poly = QPolygonF([self.image_to_screen(p) for p in self.vertices])
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setBrush(QBrush(QColor(80, 180, 255, 60)))
            painter.setPen(QPen(QColor(80, 180, 255, 220), 2))
            painter.drawPolygon(poly)

            occupancy: dict[tuple[float, float], int] = {}
            for p in self.vertices:
                key = (round(p.x(), 6), round(p.y(), 6))
                occupancy[key] = occupancy.get(key, 0) + 1

            for i, p in enumerate(self.vertices):
                sp = self.image_to_screen(p)
                key = (round(p.x(), 6), round(p.y(), 6))
                is_duplicate = occupancy[key] > 1

                if i == self.dragging_index:
                    border_color, border_width = QColor(255, 210, 60), 2.5
                elif i == self.selected_index:
                    border_color, border_width = QColor(255, 140, 60), 2.5
                elif i == self.hover_index:
                    border_color, border_width = QColor(255, 255, 255), 2.0
                else:
                    border_color, border_width = QColor(20, 20, 20), 1.0

                fill_color = QColor(235, 60, 60) if is_duplicate else QColor(80, 180, 255)

                painter.setBrush(QBrush(fill_color))
                painter.setPen(QPen(border_color, border_width))
                painter.drawEllipse(sp, POINT_RADIUS, POINT_RADIUS)

        painter.end()

    def _draw_circle_hitbox(self, painter: QPainter) -> None:
        center_screen, handle_screen = self._circle_handle_screen_pos()
        radius_screen = self.circle_radius * self.zoom

        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setBrush(QBrush(QColor(80, 180, 255, 60)))
        painter.setPen(QPen(QColor(80, 180, 255, 220), 2))
        painter.drawEllipse(center_screen, radius_screen, radius_screen)

        # Center handle
        if self.dragging_circle_center:
            border_color, border_width = QColor(255, 210, 60), 2.5
        elif self.hover_circle_center:
            border_color, border_width = QColor(255, 255, 255), 2.0
        else:
            border_color, border_width = QColor(20, 20, 20), 1.0
        painter.setBrush(QBrush(QColor(80, 180, 255)))
        painter.setPen(QPen(border_color, border_width))
        painter.drawEllipse(center_screen, POINT_RADIUS, POINT_RADIUS)

        # Radius handle
        if self.dragging_circle_radius:
            border_color, border_width = QColor(255, 210, 60), 2.5
        elif self.hover_circle_radius:
            border_color, border_width = QColor(255, 255, 255), 2.0
        else:
            border_color, border_width = QColor(20, 20, 20), 1.0
        painter.setBrush(QBrush(QColor(255, 140, 60)))
        painter.setPen(QPen(border_color, border_width))
        painter.drawEllipse(handle_screen, POINT_RADIUS, POINT_RADIUS)

    def _draw_pixel_grid(self, painter: QPainter) -> None:
        w2, h2 = self.img_w / 2, self.img_h / 2
        tl = self.screen_to_image(QPointF(0, 0))
        br = self.screen_to_image(QPointF(self.width(), self.height()))
        x0 = max(-w2, min(w2, tl.x()))
        x1 = max(-w2, min(w2, br.x()))
        y0 = max(-h2, min(h2, tl.y()))
        y1 = max(-h2, min(h2, br.y()))

        pen = QPen(QColor(255, 255, 255, 55))
        pen.setWidth(0)
        painter.setPen(pen)

        start_x = int(math.floor(x0 + w2))
        end_x = int(math.ceil(x1 + w2))
        for gx in range(start_x, end_x + 1):
            ix = gx - w2
            if ix < x0 - 1 or ix > x1 + 1:
                continue
            p1 = self.image_to_screen(QPointF(ix, y0))
            p2 = self.image_to_screen(QPointF(ix, y1))
            painter.drawLine(p1, p2)

        start_y = int(math.floor(y0 + h2))
        end_y = int(math.ceil(y1 + h2))
        for gy in range(start_y, end_y + 1):
            iy = gy - h2
            if iy < y0 - 1 or iy > y1 + 1:
                continue
            p1 = self.image_to_screen(QPointF(x0, iy))
            p2 = self.image_to_screen(QPointF(x1, iy))
            painter.drawLine(p1, p2)

    def _draw_hovered_pixel(self, painter: QPainter, hover_pixel: tuple[int, int]) -> None:
        px, py = hover_pixel
        w2, h2 = self.img_w / 2, self.img_h / 2
        cell_tl = self.image_to_screen(QPointF(px - w2, py - h2))
        cell_br = self.image_to_screen(QPointF(px - w2 + 1, py - h2 + 1))
        rect = QRectF(cell_tl, cell_br)
        painter.setPen(QPen(QColor(255, 255, 0, 200), 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)

        center = self.image_to_screen(QPointF(px - w2 + 0.5, py - h2 + 0.5))
        painter.drawLine(QPointF(center.x() - 4, center.y()), QPointF(center.x() + 4, center.y()))
        painter.drawLine(QPointF(center.x(), center.y() - 4), QPointF(center.x(), center.y() + 4))

    # ------------------------------------------------------------------ #
    # Hit-testing in screen space
    # ------------------------------------------------------------------ #
    def _circle_handle_screen_pos(self) -> tuple[QPointF, QPointF]:
        """Returns (center, radius-handle) screen positions for the circle hitbox.
        The radius handle sits on the circle's edge along the +x direction."""
        center_screen = self.image_to_screen(self.circle_center)
        radius_screen = self.circle_radius * self.zoom
        handle_screen = QPointF(center_screen.x() + radius_screen, center_screen.y())
        return center_screen, handle_screen

    def _circle_center_hit(self, screen_pt: QPointF) -> bool:
        center_screen, _ = self._circle_handle_screen_pos()
        dist = ((center_screen.x() - screen_pt.x()) ** 2 + (center_screen.y() - screen_pt.y()) ** 2) ** 0.5
        return dist < POINT_HIT_RADIUS

    def _circle_radius_handle_hit(self, screen_pt: QPointF) -> bool:
        _, handle_screen = self._circle_handle_screen_pos()
        dist = ((handle_screen.x() - screen_pt.x()) ** 2 + (handle_screen.y() - screen_pt.y()) ** 2) ** 0.5
        return dist < POINT_HIT_RADIUS

    def _vertex_at(self, screen_pt: QPointF) -> int | None:
        best_i, best_d = None, POINT_HIT_RADIUS
        for i, p in enumerate(self.vertices):
            sp = self.image_to_screen(p)
            dist = ((sp.x() - screen_pt.x()) ** 2 + (sp.y() - screen_pt.y()) ** 2) ** 0.5
            if dist < best_d:
                best_d = dist
                best_i = i
        return best_i

    def _edge_insert_at(self, screen_pt: QPointF) -> tuple[int, QPointF] | None:
        n = len(self.vertices)
        if n < 2:
            return None
        best = None
        best_d = POINT_HIT_RADIUS
        for i in range(n):
            a = self.image_to_screen(self.vertices[i])
            b = self.image_to_screen(self.vertices[(i + 1) % n])
            ab = QPointF(b.x() - a.x(), b.y() - a.y())
            length_sq = ab.x() ** 2 + ab.y() ** 2
            if length_sq == 0:
                continue
            t = ((screen_pt.x() - a.x()) * ab.x() + (screen_pt.y() - a.y()) * ab.y()) / length_sq
            t = max(0.0, min(1.0, t))
            proj = QPointF(a.x() + ab.x() * t, a.y() + ab.y() * t)
            dist = ((proj.x() - screen_pt.x()) ** 2 + (proj.y() - screen_pt.y()) ** 2) ** 0.5
            if dist < best_d:
                best_d = dist
                best = (i + 1, self.screen_to_image(proj))
        return best

    # ------------------------------------------------------------------ #
    # Mouse / keyboard events
    # ------------------------------------------------------------------ #
    def wheelEvent(self, event) -> None:
        if not self.pixmap:
            return
        cursor = event.position()
        before = self.screen_to_image(cursor)
        steps = event.angleDelta().y() / 120.0
        factor = 1.15 ** steps
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, self.zoom * factor))
        self.zoom = new_zoom
        self.pan = QPointF(cursor.x() - before.x() * self.zoom, cursor.y() - before.y() * self.zoom)
        self.update()
        self._emit_status(cursor)

    def mousePressEvent(self, event) -> None:
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        pos = event.position()

        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space_held
        ):
            self.panning = True
            self._last_mouse = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton and self.pixmap and self.shape == HitboxShapes.CIRCLE:
            if self._circle_radius_handle_hit(pos):
                self.push_history()
                self.dragging_circle_radius = True
                self.update()
                return
            if self._circle_center_hit(pos):
                self.push_history()
                self.dragging_circle_center = True
                self.update()
                return

        if event.button() == Qt.MouseButton.LeftButton and self.pixmap and self.shape == HitboxShapes.POLYGON:
            idx = self._vertex_at(pos)
            if idx is not None:
                self.push_history()
                self.dragging_index = idx
                self.selected_index = idx
                self.update()
                return
            if len(self.vertices) < 3:
                self.push_history()
                self.vertices.append(self.snap_point_to_pixel_grid(self.screen_to_image(pos)))
                self.selected_index = len(self.vertices) - 1
                self.verticesChanged.emit(self.get_vertices())
                self.update()
                return

        if event.button() == Qt.MouseButton.RightButton and self.pixmap and self.shape == HitboxShapes.POLYGON:
            idx = self._vertex_at(pos)
            if idx is not None:
                if len(self.vertices) > 3:
                    self.push_history()
                    del self.vertices[idx]
                    self.selected_index = None
                    self.verticesChanged.emit(self.get_vertices())
                    self.update()
                else:
                    self.statusChanged.emit(self.translate("HitboxCanvas", "Cannot delete - hitbox requires at least 3 vertices.", None))

    def mouseDoubleClickEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.shape == HitboxShapes.POLYGON and self.pixmap and len(self.vertices) >= 3:
            hit = self._edge_insert_at(event.position())
            if hit is not None:
                idx, pt = hit
                pt = self.snap_point_to_pixel_grid(pt)
                self.push_history()
                self.vertices.insert(idx, pt)
                self.selected_index = idx
                self.verticesChanged.emit(self.get_vertices())
                self.update()

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()

        if self.panning:
            delta = pos - self._last_mouse
            self.pan = self.pan + delta
            self._last_mouse = pos
            self.update()
            self._emit_status(pos)
            return

        if self.dragging_circle_center:
            pt = self.snap_point_to_pixel_grid(self.screen_to_image(pos))
            self.circle_center = pt
            self.circleChanged.emit(self.get_circle())
            self.update()
            self._emit_status(pos)
            return

        if self.dragging_circle_radius:
            img_pt = self.screen_to_image(pos)
            dx = img_pt.x() - self.circle_center.x()
            dy = img_pt.y() - self.circle_center.y()
            self.circle_radius = max(0.5, round((dx * dx + dy * dy) ** 0.5))
            self.circleChanged.emit(self.get_circle())
            self.update()
            self._emit_status(pos)
            return

        if self.dragging_index is not None:
            pt = self.snap_point_to_pixel_grid(self.screen_to_image(pos))
            self.vertices[self.dragging_index] = pt
            self.verticesChanged.emit(self.get_vertices())
            self.update()
            self._emit_status(pos)
            return

        if self.pixmap and self.shape == HitboxShapes.POLYGON:
            old_hover = self.hover_index
            self.hover_index = self._vertex_at(pos)
            if self.hover_index != old_hover:
                self.setCursor(
                    Qt.CursorShape.PointingHandCursor if self.hover_index is not None else Qt.CursorShape.ArrowCursor
                )
                self.update()
        elif self.pixmap and self.shape == HitboxShapes.CIRCLE:
            old_hover_circle = (self.hover_circle_center, self.hover_circle_radius)
            self.hover_circle_radius = self._circle_radius_handle_hit(pos)
            self.hover_circle_center = (not self.hover_circle_radius) and self._circle_center_hit(pos)
            if (self.hover_circle_center, self.hover_circle_radius) != old_hover_circle:
                self.setCursor(
                    Qt.CursorShape.PointingHandCursor
                    if (self.hover_circle_center or self.hover_circle_radius)
                    else Qt.CursorShape.ArrowCursor
                )
                self.update()

        self._emit_status(pos)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton) and self.panning:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_index is not None:
            self.dragging_index = None
            self.update()
        if event.button() == Qt.MouseButton.LeftButton and (self.dragging_circle_center or self.dragging_circle_radius):
            self.dragging_circle_center = False
            self.dragging_circle_radius = False
            self.update()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._space_held = True
            return
        step = 1.0
        if self.selected_index is not None and self.selected_index < len(self.vertices):
            moved = True
            p = self.vertices[self.selected_index]
            if event.key() == Qt.Key.Key_Left:
                p = QPointF(p.x() - step, p.y())
            elif event.key() == Qt.Key.Key_Right:
                p = QPointF(p.x() + step, p.y())
            elif event.key() == Qt.Key.Key_Up:
                p = QPointF(p.x(), p.y() - step)
            elif event.key() == Qt.Key.Key_Down:
                p = QPointF(p.x(), p.y() + step)
            elif event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
                if len(self.vertices) > 3:
                    self.push_history()
                    del self.vertices[self.selected_index]
                    self.selected_index = None
                    self.verticesChanged.emit(self.get_vertices())
                self.update()
                return
            else:
                moved = False
            if moved:
                self.vertices[self.selected_index] = self.snap_point_to_pixel_grid(p)
                self.verticesChanged.emit(self.get_vertices())
                self.update()
                self._emit_status()
                return
        if event.key() == Qt.Key.Key_Escape:
            self.selected_index = None
            self.update()
        super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Space:
            self._space_held = False
        super().keyReleaseEvent(event)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)

    @property
    def _hover_pixel(self) -> tuple[int, int] | None:
        if not self.pixmap:
            return None
        pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(pos):
            return None
        img_pt = self.screen_to_image(QPointF(pos))
        return self.pixel_index_at(img_pt)

    def _emit_status(self, screen_pos: QPointF | None = None) -> None:
        if not self.pixmap:
            self.statusChanged.emit(self.translate("HitboxCanvas", "No image loaded. Ctrl+O to open one.", None))
            return
        zoom_label = self.translate("HitboxCanvas", "Zoom:", None)
        if self.shape == HitboxShapes.CIRCLE:
            radius_label = self.translate("HitboxCanvas", "Radius:", None)
            parts = [
                f"{zoom_label} {self.zoom * 100:.0f}%",
                f"{radius_label} {self.circle_radius:.1f}",
            ]
        else:
            vertices_label = self.translate("HitboxCanvas", "Vertices:", None)
            parts = [
                f"{zoom_label} {self.zoom * 100:.0f}%",
                f"{vertices_label} {len(self.vertices)}",
            ]
        if screen_pos is not None:
            img_pt = self.screen_to_image(screen_pos)
            image_label = self.translate("HitboxCanvas", "Image:", None)
            parts.append(f"{image_label} ({img_pt.x():.2f}, {img_pt.y():.2f})")
            px = self.pixel_index_at(img_pt)
            if px is not None and self.image is not None:
                alpha = self.image.pixelColor(px[0], px[1]).alpha()
                pixel_label = self.translate("HitboxCanvas", "Pixel:", None)
                parts.append(f"{pixel_label} {px[0]},{px[1]} (alpha={alpha})")
        self.statusChanged.emit("   |   ".join(parts))

class PolygonOptionsWidget(QWidget):
    alphaChanged = Signal(int)
    toleranceChanged = Signal(float)
    recomputeClicked = Signal()

    translate = QCoreApplication.translate

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_alpha = QLabel(self.translate("ObjectsEditor", "Alpha threshold:", None))
        layout.addWidget(self.lbl_alpha)
        self.alpha_spin = QSpinBox()
        self.alpha_spin.setRange(0, 255)
        self.alpha_spin.setValue(20)
        layout.addWidget(self.alpha_spin)
        self.alpha_spin.valueChanged.connect(self.alphaChanged)
        
        self.lbl_tolerance = QLabel(self.translate("ObjectsEditor", "Tolerance:", None))
        layout.addWidget(self.lbl_tolerance)
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.0, 20.0)
        self.tolerance_spin.setSingleStep(0.1)
        self.tolerance_spin.setValue(0)
        layout.addWidget(self.tolerance_spin)
        self.tolerance_spin.valueChanged.connect(self.toleranceChanged)

        self.recompute_btn = QPushButton(self.translate("ObjectsEditor", "Recompute hull", None))
        layout.addWidget(self.recompute_btn)
        self.recompute_btn.clicked.connect(self.recomputeClicked)

        layout.addStretch()

class CircleOptionsWidget(QWidget):
    radiusChanged = Signal(float)

    translate = QCoreApplication.translate

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.lbl_radius = QLabel(self.translate("ObjectsEditor", "Radius:", None))
        layout.addWidget(self.lbl_radius)
        self.radius_spin = QDoubleSpinBox()
        self.radius_spin.setRange(0.5, 100000)
        self.radius_spin.setDecimals(1)
        layout.addWidget(self.radius_spin)
        self.radius_spin.valueChanged.connect(self.radiusChanged)

        layout.addStretch()

    def set_radius(self, radius: float) -> None:
        self.radius_spin.blockSignals(True)
        self.radius_spin.setValue(radius)
        self.radius_spin.blockSignals(False)

class HitboxOptionsWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)

        self.stack = QStackedWidget()
        self.pages: dict[str, QWidget] = {}

        self.polygon = PolygonOptionsWidget()
        self.register_page(HitboxShapes.POLYGON, self.polygon)
        
        self.circle = CircleOptionsWidget()
        self.register_page(HitboxShapes.CIRCLE, self.circle)

        layout.addWidget(self.stack)
        layout.addStretch()

    def register_page(self, shape: str, widget: QWidget) -> None:
        self.pages[shape] = widget
        self.stack.addWidget(widget)

    def set_shape(self, shape) -> None:
        widget = self.pages.get(shape)

        if widget is not None:
            self.stack.setCurrentWidget(widget)

class MainWindow(QMainWindow):
    translate = QCoreApplication.translate

    def __init__(self, translator: Translator | None = None, image_path: str | None = None) -> None:
        super().__init__()
        self.translator = translator or Translator("en")

        self.current_image_path: str | None = None
        self._dirty: bool = False
        self.translator.tr(lambda: self._update_window_title())
        self.resize(1100, 750)
        self.setWindowIcon(QIcon("icon.ico"))

        self.canvas = HitboxCanvas(self, translator=self.translator)
        self.setCentralWidget(self.canvas)
        self.canvas.statusChanged.connect(self._on_status_changed)
        self.canvas.verticesChanged.connect(self._on_vertices_changed)
        self.canvas.shapeChanged.connect(self._on_canvas_shape_changed)
        self.canvas.circleChanged.connect(self._on_circle_changed)

        self._build_menu()
        self._build_toolbar()
        self._build_physics_toolbar()
        self._build_statusbar()

        if image_path:
            self._load_image_from_path(image_path)

    def _update_window_title(self) -> None:
        '''Sets the window title, re-run whenever the language changes or a new image is loaded.'''
        title = self.translate("ObjectsEditor", "Objects Editor", None)
        if self.current_image_path:
            title = f"{title} - {Path(self.current_image_path).name}"
        self.setWindowTitle(title)

    # ------------------------------------------------------------------ #
    def _build_menu(self) -> None:
        menubar = self.menuBar()

        file_menu = menubar.addMenu("")
        self.translator.tr(lambda: file_menu.setTitle(self.translate("ObjectsEditor", "File", None)))

        act_open_img = QAction(self)
        self.translator.tr(lambda: act_open_img.setText(self.translate("ObjectsEditor", "Open image...", None)))
        act_open_img.setShortcut(QKeySequence("Ctrl+O"))
        act_open_img.triggered.connect(lambda: self._load_image_from_path(None))
        file_menu.addAction(act_open_img)

        act_save_hb = QAction(self)
        self.translator.tr(lambda: act_save_hb.setText(self.translate("ObjectsEditor", "Save changes", None)))
        act_save_hb.setShortcut(QKeySequence("Ctrl+S"))
        act_save_hb.triggered.connect(self._save_hitbox)
        file_menu.addAction(act_save_hb)

        file_menu.addSeparator()
        act_quit = QAction(self)
        self.translator.tr(lambda: act_quit.setText(self.translate("ObjectsEditor", "Close", None)))
        act_quit.setShortcut(QKeySequence("Ctrl+Q"))
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        edit_menu = menubar.addMenu("")
        self.translator.tr(lambda: edit_menu.setTitle(self.translate("ObjectsEditor", "Edit", None)))

        act_undo = QAction(self)
        self.translator.tr(lambda: act_undo.setText(self.translate("ObjectsEditor", "Undo", None)))
        act_undo.setShortcut(QKeySequence("Ctrl+Z"))
        act_undo.triggered.connect(self.canvas.undo)
        edit_menu.addAction(act_undo)

        act_redo = QAction(self)
        self.translator.tr(lambda: act_redo.setText(self.translate("ObjectsEditor", "Redo", None)))
        act_redo.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        act_redo.triggered.connect(self.canvas.redo)
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()

        act_recompute = QAction(self)
        self.translator.tr(lambda: act_recompute.setText(self.translate("ObjectsEditor", "Generate hitbox from image", None)))
        act_recompute.setShortcut(QKeySequence("R"))
        act_recompute.triggered.connect(lambda: self.canvas.recompute_default_hull(push_undo=True))
        edit_menu.addAction(act_recompute)

        act_bbox = QAction(self)
        self.translator.tr(lambda: act_bbox.setText(self.translate("ObjectsEditor", "Set hitbox to full image (bounding box)", None)))
        act_bbox.setShortcut(QKeySequence("Shift+R"))
        act_bbox.triggered.connect(self.canvas.reset_bounding_box)
        edit_menu.addAction(act_bbox)

        view_menu = menubar.addMenu("")
        self.translator.tr(lambda: view_menu.setTitle(self.translate("ObjectsEditor", "View", None)))

        act_fit = QAction(self)
        self.translator.tr(lambda: act_fit.setText(self.translate("ObjectsEditor", "Fit view", None)))
        act_fit.setShortcut(QKeySequence("F"))
        act_fit.triggered.connect(self.canvas.fit_to_view)
        view_menu.addAction(act_fit)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar(self)
        self.translator.tr(lambda: toolbar.setWindowTitle(self.translate("ObjectsEditor", "Tools", None)))
        self.addToolBar(toolbar)

        self.hitbox_options = HitboxOptionsWidget()
        toolbar.addWidget(self.hitbox_options)

        polygon = self.hitbox_options.polygon
        polygon.alphaChanged.connect(self._on_alpha_changed)
        polygon.toleranceChanged.connect(self._on_tolerance_changed)
        polygon.recomputeClicked.connect(lambda: self.canvas.recompute_default_hull(True))

        circle = self.hitbox_options.circle
        circle.radiusChanged.connect(self._on_radius_changed)

        toolbar.addSeparator()

        self.grid_checkbox = QCheckBox(self)
        self.translator.tr(lambda: self.grid_checkbox.setText(self.translate("ObjectsEditor", "Show pixel grid", None)))
        self.grid_checkbox.setChecked(self.canvas.show_grid)
        self.grid_checkbox.toggled.connect(self._on_grid_toggled)
        toolbar.addWidget(self.grid_checkbox)

        toolbar.addSeparator()
        act_fit_tb = QAction(self)
        self.translator.tr(lambda: act_fit_tb.setText(self.translate("ObjectsEditor", "Fit view (F)", None)))
        act_fit_tb.triggered.connect(self.canvas.fit_to_view)
        toolbar.addAction(act_fit_tb)

        self.hitbox_options.set_shape(self.canvas.shape)

    def _build_physics_toolbar(self) -> None:
        toolbar = QToolBar(self)
        self.translator.tr(lambda: toolbar.setWindowTitle(self.translate("ObjectsEditor", "Physics properties", None)))
        self.addToolBarBreak()
        self.addToolBar(toolbar)

        lbl_shape = QLabel()
        self.translator.tr(lambda: lbl_shape.setText(self.translate("ObjectsEditor", "Hitbox shape:", None)))
        toolbar.addWidget(lbl_shape)
        self.shape_combo = QComboBox(self)
        self.shape_combo.addItem(self.translate("ObjectsEditor", "Convex polygon", None), HitboxShapes.POLYGON)
        self.shape_combo.addItem(self.translate("ObjectsEditor", "Circle", None), HitboxShapes.CIRCLE)
        self.shape_combo.currentIndexChanged.connect(self._on_shape_combo_changed)
        toolbar.addWidget(self.shape_combo)

        toolbar.addSeparator()

        lbl_mass = QLabel()
        self.translator.tr(lambda: lbl_mass.setText(self.translate("ObjectsEditor", "Mass:", None)))
        toolbar.addWidget(lbl_mass)
        self.mass_spin = QDoubleSpinBox(self)
        self.mass_spin.setRange(0.01, 1000.0)
        self.mass_spin.setSingleStep(0.1)
        self.mass_spin.setDecimals(3)
        self.mass_spin.setValue(DEFAULT_MASS)
        toolbar.addWidget(self.mass_spin)

        lbl_friction = QLabel()
        self.translator.tr(lambda: lbl_friction.setText(self.translate("ObjectsEditor", "Friction:", None)))
        toolbar.addWidget(lbl_friction)
        self.friction_spin = QDoubleSpinBox(self)
        self.friction_spin.setRange(0.0, 5.0)
        self.friction_spin.setSingleStep(0.05)
        self.friction_spin.setDecimals(3)
        self.friction_spin.setValue(DEFAULT_FRICTION)
        toolbar.addWidget(self.friction_spin)

        lbl_elasticity = QLabel()
        self.translator.tr(lambda: lbl_elasticity.setText(self.translate("ObjectsEditor", "Elasticity:", None)))
        toolbar.addWidget(lbl_elasticity)
        self.elasticity_spin = QDoubleSpinBox(self)
        self.elasticity_spin.setRange(0.0, 2.0)
        self.elasticity_spin.setSingleStep(0.05)
        self.elasticity_spin.setDecimals(3)
        self.elasticity_spin.setValue(DEFAULT_ELASTICITY)
        toolbar.addWidget(self.elasticity_spin)

        lbl_angular_damping = QLabel()
        self.translator.tr(lambda: lbl_angular_damping.setText(self.translate("ObjectsEditor", "Angular damping:", None)))
        toolbar.addWidget(lbl_angular_damping)
        self.angular_damping_spin = QDoubleSpinBox(self)
        self.angular_damping_spin.setRange(0.0, 2.0)
        self.angular_damping_spin.setSingleStep(0.05)
        self.angular_damping_spin.setDecimals(3)
        self.angular_damping_spin.setValue(DEFAULT_ANGULAR_DAMPING)
        toolbar.addWidget(self.angular_damping_spin)

        lbl_linear_damping = QLabel()
        self.translator.tr(lambda: lbl_linear_damping.setText(self.translate("ObjectsEditor", "Linear damping:", None)))
        toolbar.addWidget(lbl_linear_damping)
        self.linear_damping_spin = QDoubleSpinBox(self)
        self.linear_damping_spin.setRange(0.0, 2.0)
        self.linear_damping_spin.setSingleStep(0.05)
        self.linear_damping_spin.setDecimals(3)
        self.linear_damping_spin.setValue(DEFAULT_LINEAR_DAMPING)
        toolbar.addWidget(self.linear_damping_spin)

    def _build_statusbar(self) -> None:
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status_label = QLabel()
        self.translator.tr(lambda: self.status_label.setText(self.translate("ObjectsEditor", "No image loaded.", None)))
        self.status.addWidget(self.status_label)

    # ------------------------------------------------------------------ #
    def _on_status_changed(self, text: str) -> None:
        self.status_label.setText(text)

    def _on_vertices_changed(self, vertices: list[tuple[float, float]]) -> None:
        self._dirty = True

    def _on_shape_combo_changed(self, index: int) -> None:
        shape = self.shape_combo.itemData(index)
        self.canvas.set_shape(shape)

    def _on_canvas_shape_changed(self, shape: str) -> None:
        idx = self.shape_combo.findData(shape)
        if idx != -1:
            self.shape_combo.blockSignals(True)
            self.shape_combo.setCurrentIndex(idx)
            self.shape_combo.blockSignals(False)
        self.hitbox_options.set_shape(self.canvas.shape)
        self._dirty = True

    def _on_radius_changed(self, value: float) -> None:
        cx, cy, _ = self.canvas.get_circle()
        self.canvas.set_circle((cx, cy), value)

    def _on_circle_changed(self, circle: tuple[float, float, float]) -> None:
        _, _, radius = circle
        self.hitbox_options.circle.set_radius(radius)
        self._dirty = True

    def _on_alpha_changed(self, value: int) -> None:
        self.canvas.alpha_threshold = value

    def _on_tolerance_changed(self, value: float) -> None:
        self.canvas.hull_tolerance = value

    def _on_grid_toggled(self, checked: bool) -> None:
        self.canvas.show_grid = checked
        self.canvas.update()

    # ------------------------------------------------------------------ #
    def _confirm_discard_unsaved_changes(self) -> bool:
        """Asks the user to confirm losing unsaved work. Returns True if it's OK to proceed."""
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self,
            self.translate("ObjectsEditor", "Unsaved changes", None),
            self.translate("ObjectsEditor", "You have unsaved changes. Continue and discard them?", None),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return answer == QMessageBox.StandardButton.Yes

    def closeEvent(self, event) -> None:
        if self._confirm_discard_unsaved_changes():
            event.accept()
        else:
            event.ignore()

    # ------------------------------------------------------------------ #
    def _load_image_from_path(self, path: str | None) -> None:
        if not self._confirm_discard_unsaved_changes():
            return
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self,
                self.translate("ObjectsEditor", "Open image", None), "Assets\\Objects",
                self.translate("ObjectsEditor", "Images (*.png *.jpg *.jpeg *.bmp *.webp)", None)
            )
            if not path:
                return
        pixmap = QPixmap(path)
        if pixmap.isNull():
            QMessageBox.critical(self, self.translate("ObjectsEditor", "Error", None),
                self.translate("ObjectsEditor", "Failed to load image:\n%1", None).replace("%1", path))
            return

        self.current_image_path = path

        companion_json = Path(path).with_suffix(".json")
        has_companion = companion_json.is_file()

        self.mass_spin.setValue(DEFAULT_MASS)
        self.friction_spin.setValue(DEFAULT_FRICTION)
        self.elasticity_spin.setValue(DEFAULT_ELASTICITY)
        self.angular_damping_spin.setValue(DEFAULT_ANGULAR_DAMPING)
        self.linear_damping_spin.setValue(DEFAULT_LINEAR_DAMPING)
        self.hitbox_options.circle.set_radius(pixmap.width() // 2)

        self.canvas.set_image(pixmap, skip_default_hull=has_companion)
        self._update_window_title()

        if has_companion:
            self._load_hitbox_from_path(str(companion_json))
            self.status_label.setText(self.translate("ObjectsEditor", "Loaded image and matching hitbox: %1", None).replace("%1", companion_json.name))

        self._dirty = False  # freshly loaded state, nothing unsaved yet

    def _load_hitbox_from_path(self, path: str) -> None:
        """Loads the hitbox geometry (polygon or circle) and physics properties from a JSON file"""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            shape = data["shape"]
            if shape == HitboxShapes.POLYGON:
                vertices: list[tuple[float, float]] = [(float(x), float(y)) for x, y in data["vertices"]]
            elif shape == HitboxShapes.CIRCLE:
                radius: float = float(data["radius"])
                raw_center = data["center"]
                center: tuple[float, float] = (float(raw_center[0]), float(raw_center[1]))
            else:
                raise Exception(f'Unknown hitbox shape "{shape}"')
            mass = float(data["mass"])
            friction = float(data["friction"])
            elasticity = float(data["elasticity"])
            angular_damping = float(data["angular_damping"])
            linear_damping = float(data["linear_damping"])
        except Exception as exc:
            self.canvas.recompute_default_hull(push_undo=False)

            QMessageBox.critical(self, self.translate("ObjectsEditor", "Error", None),
                self.translate("ObjectsEditor", "Failed to load JSON file:\n%1", None).replace("%1", str(exc)))
            return
        if not self.canvas.pixmap:
            QMessageBox.warning(self, self.translate("ObjectsEditor", "Warning", None),
                self.translate("ObjectsEditor", "Open an image first to edit its hitbox.", None))
            return
        self.canvas.set_shape(shape)
        if shape == HitboxShapes.CIRCLE:
            self.canvas.set_circle(center, radius, push_undo=False)
        else:
            self.canvas.set_vertices(vertices)
        self.mass_spin.setValue(mass)
        self.friction_spin.setValue(friction)
        self.elasticity_spin.setValue(elasticity)
        self.angular_damping_spin.setValue(angular_damping)
        self.linear_damping_spin.setValue(linear_damping)

        self.status_label.setText(self.translate("ObjectsEditor", "Loaded hitbox: %1", None).replace("%1", Path(path).name))

    def _save_hitbox(self) -> None:
        if not self.canvas.pixmap or not self.current_image_path:
            QMessageBox.warning(self, self.translate("ObjectsEditor", "Warning", None),
                self.translate("ObjectsEditor", "Open an image first.", None))
            return
        if self.canvas.shape == HitboxShapes.POLYGON and not self.canvas.vertices:
            QMessageBox.warning(self, self.translate("ObjectsEditor", "Warning", None),
                self.translate("ObjectsEditor", "No vertices to save.", None))
            return

        json_path = Path(self.current_image_path).with_suffix(".json")

        if json_path.is_file():
            answer = QMessageBox.question(
                self,
                self.translate("ObjectsEditor", "Overwrite file?", None),
                self.translate("ObjectsEditor", "The file %1 already exists. Overwrite it?", None).replace("%1", json_path.name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        data: dict = {
            "shape": self.canvas.shape,
            "mass": self.mass_spin.value(),
            "friction": self.friction_spin.value(),
            "elasticity": self.elasticity_spin.value(),
            "angular_damping": self.angular_damping_spin.value(),
            "linear_damping": self.linear_damping_spin.value(),
        }
        if self.canvas.shape == HitboxShapes.POLYGON:
            vertex_count = len(self.canvas.vertices)
            if vertex_count > MAX_POLYGON_VERTICES:
                QMessageBox.warning(
                    self,
                    self.translate("ObjectsEditor", "Warning", None),
                    self.translate("ObjectsEditor", "The hitbox has %1 vertices, more than the %2 Box2D allows per polygon.\n"
                        "It will be simplified automatically when used, which may change its shape. Saving anyway.", None)
                        .replace("%1", str(vertex_count)).replace("%2", str(MAX_POLYGON_VERTICES)),
                )
            data = data | {
                "vertices": self.canvas.get_vertices(),
            }
        elif self.canvas.shape == HitboxShapes.CIRCLE:
            cx, cy, radius = self.canvas.get_circle()
            data = data | {
                "center": [cx, cy],
                "radius": radius,
            }
        else:
            raise Exception(f'Unknown hitbox shape "{self.canvas.shape}"')

        try:
            json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, self.translate("ObjectsEditor", "Error", None),
                self.translate("ObjectsEditor", "Failed to save JSON file:\n%1", None).replace("%1", str(exc)))
            return

        self._dirty = False
        self.status_label.setText(self.translate("ObjectsEditor", "Saved: %1", None).replace("%1", json_path.name))

def main() -> None:
    import argparse
    import sys
    parser = argparse.ArgumentParser(description="Object editor with image preview.")
    parser.add_argument("image", nargs="?", default=None, help="Path to the image (optional)")
    args = parser.parse_args()

    app = QApplication(sys.argv)
    window = MainWindow(image_path=args.image)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
