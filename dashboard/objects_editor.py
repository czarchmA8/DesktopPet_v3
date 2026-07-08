import json
import math
from pathlib import Path
import pymunk
import pymunk.autogeometry
import numpy as np
from PySide6.QtCore import Qt, QPointF, QRectF, QSizeF, Signal, QTimer, QCoreApplication
from PySide6.QtGui import (
    QAction, QBrush, QColor,
    QCursor, QGuiApplication, QImage,
    QKeySequence, QPainter, QPen,
    QPixmap, QPolygonF, QIcon
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox,
    QFileDialog, QLabel, QMainWindow,
    QMessageBox, QSpinBox, QStatusBar,
    QToolBar, QWidget
)

from dashboard.translator import Translator

DEFAULT_HULL: list[tuple[float, float]] = [(-10.0, -10.0), (10.0, -10.0), (10.0, 10.0), (-10.0, 10.0)]

VERTEX_RADIUS = 5.0          # radius of the drawn vertex on the screen (px)
VERTEX_HIT_RADIUS = 9.0      # tolerance for "grabbing" a vertex with the mouse (screen px)
EDGE_HIT_RADIUS = 7.0        # tolerance for inserting a vertex on an edge (screen px)
MIN_ZOOM = 0.05
MAX_ZOOM = 256.0
GRID_MIN_ZOOM = 6.0          # from what zoom level to draw the pixel grid
MAX_HISTORY = 100

# Default physics properties assigned to a new object
DEFAULT_MASS = 1.0
DEFAULT_FRICTION = 0.5
DEFAULT_ELASTICITY = 0.3

def generate_hull_vertices(pixmap: QPixmap, alpha_threshold: int = 20, tolerance: float = 0.0) -> list[tuple[float, float]] | list[list[float]]:
    """Generates convex hull vertices based on the image's transparency."""
    image = pixmap.toImage()
    width, height = image.width(), image.height()
    if width == 0 or height == 0:
        return list(DEFAULT_HULL)

    img = image.convertToFormat(QImage.Format.Format_RGBA8888)
    buf = img.constBits()
    arr = np.frombuffer(buf, dtype=np.uint8, count=height * img.bytesPerLine())
    arr = arr.reshape((height, img.bytesPerLine()))[:, : width * 4].reshape((height, width, 4))
    alpha = arr[:, :, 3]
    ys, xs = np.nonzero(alpha > alpha_threshold)

    if xs.size == 0:
        return list(DEFAULT_HULL)

    w2, h2 = width / 2.0, height / 2.0
    xs = xs.astype(np.float64)
    ys = ys.astype(np.float64)
    corner_dx = np.array([0.0, 1.0, 1.0, 0.0])
    corner_dy = np.array([0.0, 0.0, 1.0, 1.0])
    px = (xs[:, None] + corner_dx[None, :] - w2).ravel()
    py = (ys[:, None] + corner_dy[None, :] - h2).ravel()
    points: list[tuple[float, float]] = list(zip(px.tolist(), py.tolist()))

    hull = pymunk.autogeometry.to_convex_hull(points, tolerance)
    if len(hull) > 1 and hull[0] == hull[-1]:
        hull = hull[:-1]
    return [(float(p[0]), float(p[1])) for p in hull]

class HitboxCanvas(QWidget):
    """A widget responsible for displaying the image and editing the hitbox polygon."""

    statusChanged = Signal(str)
    verticesChanged = Signal(list)
    translate = QCoreApplication.translate

    def __init__(self, parent: QWidget | None = None, translator: Translator | None = None):
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

        self.zoom = 1.0
        self.pan = QPointF(0.0, 0.0)

        self.show_grid = True
        self.alpha_threshold = 20
        self.hull_tolerance = 0.0

        # Physics properties of the object
        self.mass = DEFAULT_MASS
        self.friction = DEFAULT_FRICTION
        self.elasticity = DEFAULT_ELASTICITY

        self.hover_index: int | None = None
        self.dragging_index: int | None = None
        self.selected_index: int | None = None
        self.panning = False
        self._last_mouse = QPointF()
        self._space_held = False

        self._undo_stack: list[list[tuple[float, float]]] = []
        self._redo_stack: list[list[tuple[float, float]]] = []

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
    def set_image(self, pixmap: QPixmap, skip_default_hull: bool = False):
        """Loads a new image"""
        self.pixmap = pixmap
        self.image = pixmap.toImage()
        self.img_w = pixmap.width()
        self.img_h = pixmap.height()
        self._undo_stack.clear()
        self._redo_stack.clear()

        self.mass = DEFAULT_MASS
        self.friction = DEFAULT_FRICTION
        self.elasticity = DEFAULT_ELASTICITY

        if skip_default_hull:
            self.vertices = []
            self.selected_index = None
        else:
            self.recompute_default_hull(push_undo=False)
        QTimer.singleShot(0, self.fit_to_view)
        self.update()

    def recompute_default_hull(self, push_undo: bool = True):
        if not self.pixmap:
            return
        if push_undo:
            self.push_history()
        hull = generate_hull_vertices(self.pixmap, self.alpha_threshold, self.hull_tolerance)
        self.vertices = [self.snap_point_to_pixel_grid(QPointF(x, y)) for x, y in hull]
        self.selected_index = None
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    def reset_bounding_box(self):
        if not self.pixmap:
            return
        self.push_history()
        w2, h2 = self.img_w / 2, self.img_h / 2
        self.vertices = [QPointF(-w2, -h2), QPointF(w2, -h2), QPointF(w2, h2), QPointF(-w2, h2)]
        self.selected_index = None
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    def get_vertices(self) -> list[tuple[float, float]]:
        return [(p.x(), p.y()) for p in self.vertices]

    def set_vertices(self, verts: list[tuple[float, float]]):
        self.push_history()
        self.vertices = [self.snap_point_to_pixel_grid(QPointF(x, y)) for x, y in verts]
        self.selected_index = None
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    def get_properties(self) -> dict[str, float]:
        return {"mass": self.mass, "friction": self.friction, "elasticity": self.elasticity}

    def set_properties(
        self,
        mass: float | None = None,
        friction: float | None = None,
        elasticity: float | None = None,
    ):
        if mass is not None:
            self.mass = mass
        if friction is not None:
            self.friction = friction
        if elasticity is not None:
            self.elasticity = elasticity

    def fit_to_view(self):
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
    def push_history(self):
        self._undo_stack.append(self.get_vertices())
        if len(self._undo_stack) > MAX_HISTORY:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self.get_vertices())
        verts = self._undo_stack.pop()
        self.vertices = [QPointF(x, y) for x, y in verts]
        self.selected_index = None
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self.get_vertices())
        verts = self._redo_stack.pop()
        self.vertices = [QPointF(x, y) for x, y in verts]
        self.selected_index = None
        self.verticesChanged.emit(self.get_vertices())
        self.update()

    # ------------------------------------------------------------------ #
    # Drawing
    # ------------------------------------------------------------------ #
    def paintEvent(self, event):
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
        if self._hover_pixel is not None and self.zoom >= GRID_MIN_ZOOM:
            self._draw_hovered_pixel(painter)

        # Hitbox polygon
        if self.vertices:
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
                painter.drawEllipse(sp, VERTEX_RADIUS, VERTEX_RADIUS)

        painter.end()

    def _draw_pixel_grid(self, painter: QPainter):
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

    def _draw_hovered_pixel(self, painter: QPainter):
        px, py = self._hover_pixel
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
    def _vertex_at(self, screen_pt: QPointF) -> int | None:
        best_i, best_d = None, VERTEX_HIT_RADIUS
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
        best_d = EDGE_HIT_RADIUS
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
    def wheelEvent(self, event):
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

    def mousePressEvent(self, event):
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        pos = event.position()

        if event.button() == Qt.MouseButton.MiddleButton or (
            event.button() == Qt.MouseButton.LeftButton and self._space_held
        ):
            self.panning = True
            self._last_mouse = pos
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return

        if event.button() == Qt.MouseButton.LeftButton and self.pixmap:
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

        if event.button() == Qt.MouseButton.RightButton and self.pixmap:
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

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.pixmap and len(self.vertices) >= 3:
            hit = self._edge_insert_at(event.position())
            if hit is not None:
                idx, pt = hit
                pt = self.snap_point_to_pixel_grid(pt)
                self.push_history()
                self.vertices.insert(idx, pt)
                self.selected_index = idx
                self.verticesChanged.emit(self.get_vertices())
                self.update()

    def mouseMoveEvent(self, event):
        pos = event.position()

        if self.panning:
            delta = pos - self._last_mouse
            self.pan = self.pan + delta
            self._last_mouse = pos
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

        if self.pixmap:
            old_hover = self.hover_index
            self.hover_index = self._vertex_at(pos)
            if self.hover_index != old_hover:
                self.setCursor(
                    Qt.CursorShape.PointingHandCursor if self.hover_index is not None else Qt.CursorShape.ArrowCursor
                )
                self.update()

        self._emit_status(pos)

    def mouseReleaseEvent(self, event):
        if event.button() in (Qt.MouseButton.MiddleButton, Qt.MouseButton.LeftButton) and self.panning:
            self.panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if event.button() == Qt.MouseButton.LeftButton and self.dragging_index is not None:
            self.dragging_index = None
            self.update()

    def keyPressEvent(self, event):
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

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Space:
            self._space_held = False
        super().keyReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)

    @property
    def _hover_pixel(self):
        if not self.pixmap:
            return None
        pos = self.mapFromGlobal(QCursor.pos())
        if not self.rect().contains(pos):
            return None
        img_pt = self.screen_to_image(QPointF(pos))
        return self.pixel_index_at(img_pt)

    def _emit_status(self, screen_pos: QPointF | None = None):
        if not self.pixmap:
            self.statusChanged.emit(self.translate("HitboxCanvas", "No image loaded. Ctrl+O to open one.", None))
            return
        zoom_label = self.translate("HitboxCanvas", "Zoom:", None)
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

class MainWindow(QMainWindow):
    translate = QCoreApplication.translate

    def __init__(self, translator: Translator | None = None, image_path: str | None = None):
        super().__init__()
        self.translator = translator or Translator("en")

        self.current_image_path: str | None = None
        self.translator.tr(lambda: self._update_window_title())
        self.resize(1100, 750)
        self.setWindowIcon(QIcon("icon.ico"))

        self.canvas = HitboxCanvas(self, translator=self.translator)
        self.setCentralWidget(self.canvas)
        self.canvas.statusChanged.connect(self._on_status_changed)
        self.canvas.verticesChanged.connect(self._on_vertices_changed)

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
    def _build_menu(self):
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

    def _build_toolbar(self):
        toolbar = QToolBar(self)
        self.translator.tr(lambda: toolbar.setWindowTitle(self.translate("ObjectsEditor", "Tools", None)))
        self.addToolBar(toolbar)

        lbl_alpha = QLabel()
        self.translator.tr(lambda: lbl_alpha.setText(self.translate("ObjectsEditor", "Alpha threshold:", None)))
        toolbar.addWidget(lbl_alpha)
        self.alpha_spin = QSpinBox(self)
        self.alpha_spin.setRange(0, 255)
        self.alpha_spin.setValue(self.canvas.alpha_threshold)
        self.alpha_spin.valueChanged.connect(self._on_alpha_changed)
        toolbar.addWidget(self.alpha_spin)

        lbl_tolerance = QLabel()
        self.translator.tr(lambda: lbl_tolerance.setText(self.translate("ObjectsEditor", "Tolerance:", None)))
        toolbar.addWidget(lbl_tolerance)
        self.tolerance_spin = QDoubleSpinBox(self)
        self.tolerance_spin.setRange(0.0, 20.0)
        self.tolerance_spin.setSingleStep(0.1)
        self.tolerance_spin.setValue(self.canvas.hull_tolerance)
        self.tolerance_spin.valueChanged.connect(self._on_tolerance_changed)
        toolbar.addWidget(self.tolerance_spin)

        act_recompute_tb = QAction(self)
        self.translator.tr(lambda: act_recompute_tb.setText(self.translate("ObjectsEditor", "Recompute hull", None)))
        act_recompute_tb.triggered.connect(lambda: self.canvas.recompute_default_hull(push_undo=True))
        toolbar.addAction(act_recompute_tb)

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

    def _build_physics_toolbar(self):
        toolbar = QToolBar(self)
        self.translator.tr(lambda: toolbar.setWindowTitle(self.translate("ObjectsEditor", "Physics properties", None)))
        self.addToolBarBreak()
        self.addToolBar(toolbar)

        lbl_mass = QLabel()
        self.translator.tr(lambda: lbl_mass.setText(self.translate("ObjectsEditor", "Mass:", None)))
        toolbar.addWidget(lbl_mass)
        self.mass_spin = QDoubleSpinBox(self)
        self.mass_spin.setRange(0.01, 1000.0)
        self.mass_spin.setSingleStep(0.1)
        self.mass_spin.setDecimals(3)
        self.mass_spin.setValue(self.canvas.mass)
        self.mass_spin.valueChanged.connect(self._on_mass_changed)
        toolbar.addWidget(self.mass_spin)

        lbl_friction = QLabel()
        self.translator.tr(lambda: lbl_friction.setText(self.translate("ObjectsEditor", "Friction:", None)))
        toolbar.addWidget(lbl_friction)
        self.friction_spin = QDoubleSpinBox(self)
        self.friction_spin.setRange(0.0, 5.0)
        self.friction_spin.setSingleStep(0.05)
        self.friction_spin.setDecimals(3)
        self.friction_spin.setValue(self.canvas.friction)
        self.friction_spin.valueChanged.connect(self._on_friction_changed)
        toolbar.addWidget(self.friction_spin)

        lbl_elasticity = QLabel()
        self.translator.tr(lambda: lbl_elasticity.setText(self.translate("ObjectsEditor", "Elasticity:", None)))
        toolbar.addWidget(lbl_elasticity)
        self.elasticity_spin = QDoubleSpinBox(self)
        self.elasticity_spin.setRange(0.0, 2.0)
        self.elasticity_spin.setSingleStep(0.05)
        self.elasticity_spin.setDecimals(3)
        self.elasticity_spin.setValue(self.canvas.elasticity)
        self.elasticity_spin.valueChanged.connect(self._on_elasticity_changed)
        toolbar.addWidget(self.elasticity_spin)

    def _build_statusbar(self):
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status_label = QLabel()
        self.translator.tr(lambda: self.status_label.setText(self.translate("ObjectsEditor", "No image loaded.", None)))
        self.status.addWidget(self.status_label)

    # ------------------------------------------------------------------ #
    def _on_status_changed(self, text: str):
        self.status_label.setText(text)

    def _on_vertices_changed(self, verts: list[tuple[float, float]]):
        pass  # miejsce na ewentualną integrację z zewnętrznym podglądem na żywo

    def _on_alpha_changed(self, value: int):
        self.canvas.alpha_threshold = value

    def _on_tolerance_changed(self, value: float):
        self.canvas.hull_tolerance = value

    def _on_grid_toggled(self, checked: bool):
        self.canvas.show_grid = checked
        self.canvas.update()

    def _on_mass_changed(self, value: float):
        self.canvas.mass = value

    def _on_friction_changed(self, value: float):
        self.canvas.friction = value

    def _on_elasticity_changed(self, value: float):
        self.canvas.elasticity = value

    def _sync_physics_spinboxes(self):
        """Refreshes the mass/friction/elasticity fields after loading values from JSON,
        without re-triggering handlers (blockSignals)."""
        for spin, value in (
            (self.mass_spin, self.canvas.mass),
            (self.friction_spin, self.canvas.friction),
            (self.elasticity_spin, self.canvas.elasticity),
        ):
            spin.blockSignals(True)
            spin.setValue(value)
            spin.blockSignals(False)

    # ------------------------------------------------------------------ #
    def _load_image_from_path(self, path: str | None):
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

        self.canvas.set_image(pixmap, skip_default_hull=has_companion)
        self._update_window_title()

        if has_companion:
            self._load_hitbox_from_path(str(companion_json), silent=True)
            self.status_label.setText(self.translate("ObjectsEditor", "Loaded image and matching hitbox: %1", None).replace("%1", companion_json.name))

    def _load_hitbox_from_path(self, path: str, silent: bool = True):
        """Loads vertices and physics properties from a JSON file"""
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            verts = [(float(x), float(y)) for x, y in data["vertices"]]
            mass = float(data.get("mass", DEFAULT_MASS))
            friction = float(data.get("friction", DEFAULT_FRICTION))
            elasticity = float(data.get("elasticity", DEFAULT_ELASTICITY))
        except Exception as exc:
            if silent:
                return
            QMessageBox.critical(self, self.translate("ObjectsEditor", "Error", None),
                self.translate("ObjectsEditor", "Failed to load JSON file:\n%1", None).replace("%1", str(exc)))
            return
        if not self.canvas.pixmap:
            QMessageBox.warning(self, self.translate("ObjectsEditor", "Warning", None),
                self.translate("ObjectsEditor", "Open an image first to edit its hitbox.", None))
            return
        self.canvas.set_vertices(verts)
        self.canvas.set_properties(mass=mass, friction=friction, elasticity=elasticity)
        self._sync_physics_spinboxes()
        if not silent:
            self.status_label.setText(self.translate("ObjectsEditor", "Loaded hitbox: %1", None).replace("%1", Path(path).name))

    def _save_hitbox(self):
        if not self.canvas.pixmap or not self.current_image_path:
            QMessageBox.warning(self, self.translate("ObjectsEditor", "Warning", None),
                self.translate("ObjectsEditor", "Open an image first.", None))
            return
        if not self.canvas.vertices:
            QMessageBox.warning(self, self.translate("ObjectsEditor", "Warning", None),
                self.translate("ObjectsEditor", "No vertices to save.", None))
            return

        json_path = Path(self.current_image_path).with_suffix(".json")
        data = {"vertices": self.canvas.get_vertices(), **self.canvas.get_properties()}
        try:
            json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            QMessageBox.critical(self, self.translate("ObjectsEditor", "Error", None),
                self.translate("ObjectsEditor", "Failed to save JSON file:\n%1", None).replace("%1", str(exc)))
            return
        self.status_label.setText(self.translate("ObjectsEditor", "Saved: %1", None).replace("%1", json_path.name))

def main():
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
