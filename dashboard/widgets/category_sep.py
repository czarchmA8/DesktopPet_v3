from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QFrame

class CategorySeparator(QWidget):
    """Category header with a line."""
    def __init__(self, category_name: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 4)
        layout.setSpacing(8)

        label = QLabel(category_name)
        label.setStyleSheet("font-weight: bold; color: #aaaaaa;")
        layout.addWidget(label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line, stretch=1)
