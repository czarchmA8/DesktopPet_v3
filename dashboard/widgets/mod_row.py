from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QSizePolicy, QToolButton, QWidget

class Ui_Form_mod_row(QWidget):
    def __init__(self):
        super().__init__()
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sizePolicy().hasHeightForWidth())
        self.setSizePolicy(sizePolicy)

        self.horizontalLayout = QHBoxLayout(self)

        self.checkBox = QCheckBox(self)

        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.checkBox.sizePolicy().hasHeightForWidth())
        self.checkBox.setSizePolicy(sizePolicy1)

        self.horizontalLayout.addWidget(self.checkBox)

        self.label = QLabel(self)
        self.label.setText("ModName")

        self.horizontalLayout.addWidget(self.label)

        self.toolButton = QToolButton(self)
        self.toolButton.setText("...")

        self.horizontalLayout.addWidget(self.toolButton)
