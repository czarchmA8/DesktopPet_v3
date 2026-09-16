from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QLabel, QSizePolicy

class AspectRatioLabel(QLabel):
    """QLabel that always scales its pixmap to fit the available space
    while preserving the image's original aspect ratio, centered."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._source_pixmap = QPixmap()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(1, 1)

        policy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)

    def setPixmap(self, pixmap):
        self._source_pixmap = pixmap
        self._apply_scaled_pixmap()

    def pixmap(self):
        return self._source_pixmap

    def resizeEvent(self, event):
        self._apply_scaled_pixmap()
        super().resizeEvent(event)

    def heightForWidth(self, width):
        if self._source_pixmap.isNull() or self._source_pixmap.width() == 0:
            return super().heightForWidth(width)
        ratio = self._source_pixmap.height() / self._source_pixmap.width()
        return int(width * ratio)

    def hasHeightForWidth(self):
        return True

    def _apply_scaled_pixmap(self):
        if self._source_pixmap.isNull():
            super().clear()
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        super().setPixmap(scaled)

class BannerLabel(QLabel):
    """QLabel with a fixed height that scales its pixmap to that height,
    centered horizontally — cropping the sides if the scaled image is
    wider than the label, or leaving it untouched (no upscaling) if narrower."""

    def __init__(self, parent=None, height=200):
        super().__init__(parent)
        self._pixmap = QPixmap()
        self.setFixedHeight(height)
        self.setMinimumWidth(1)

    def setPixmap(self, pixmap):
        self._pixmap = pixmap
        self.update()

    def pixmap(self):
        return self._pixmap

    def paintEvent(self, event):
        if self._pixmap.isNull():
            return super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        scaled_pixmap = self._pixmap.scaledToHeight(self.height(), Qt.TransformationMode.SmoothTransformation)

        x = (self.width() - scaled_pixmap.width()) // 2
        y = (self.height() - scaled_pixmap.height()) // 2

        painter.drawPixmap(x, y, scaled_pixmap)
