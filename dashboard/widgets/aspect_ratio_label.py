from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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
            return
        scaled = self._source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        super().setPixmap(scaled)
