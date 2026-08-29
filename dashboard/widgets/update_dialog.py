from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel,
    QFrame, QSizePolicy, QSpacerItem,
    QDialogButtonBox
)
from PySide6.QtGui import QFont

import config
from dashboard.translator import replace_format

class UpdateDialog(QDialog):
    def __init__(self, new_version, new_version_date, parent=None):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("UpdateDialog", "Update detected", None))

        self.verticalLayout = QVBoxLayout(self)

        self.verticalLayout_2 = QVBoxLayout()

        # Główna etykieta informacyjna
        self.label_title = QLabel(self)
        sizePolicy_max = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy_max.setHorizontalStretch(0)
        sizePolicy_max.setVerticalStretch(0)
        self.label_title.setSizePolicy(sizePolicy_max)

        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.label_title.setFont(font)
        self.label_title.setText(replace_format(QCoreApplication.translate("UpdateDialog",
            "<html><head/><body><p>A new version %1 from %2 is available.<br/>Would you like to update the app?</p></body></html>",
        None), new_version, new_version_date))
        self.label_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.verticalLayout_2.addWidget(self.label_title)

        # Ramka z informacjami o wersji i linkiem
        self.frame = QFrame(self)
        sizePolicy_frame = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        sizePolicy_frame.setHorizontalStretch(0)
        sizePolicy_frame.setVerticalStretch(0)
        self.frame.setSizePolicy(sizePolicy_frame)

        self.verticalLayout_3 = QVBoxLayout(self.frame)

        # Etykieta wersji
        self.label_version_update_to = QLabel(self.frame)
        self.label_version_update_to.setSizePolicy(sizePolicy_max)
        self.label_version_update_to.setText(replace_format(QCoreApplication.translate("UpdateDialog", 'The version will be updated from "%1" to "%2"', None), config.APP_VERSION, new_version))
        self.verticalLayout_3.addWidget(self.label_version_update_to)

        # Etykieta z linkiem do GitHub
        self.label_latest_release = QLabel(self.frame)
        self.label_latest_release.setText(replace_format(QCoreApplication.translate("UpdateDialog",
            "<html><head/><body><p>Latest release: "
            '<a href="%1">'
            '<span style=" text-decoration: underline; color:#9cebff;">'
            "%1</span></a></p></body></html>",
        None), f"https://github.com/{config.APP_AUTHOR}/{config.REPO_NAME}/releases/latest"))
        self.label_latest_release.setOpenExternalLinks(True)
        self.verticalLayout_3.addWidget(self.label_latest_release)

        # Spacer wewnątrz ramki
        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.verticalLayout_3.addItem(self.verticalSpacer_2)

        # Przyciski Yes / No
        self.buttonBox = QDialogButtonBox(self.frame)
        self.buttonBox.setObjectName("buttonBox")
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.No | QDialogButtonBox.StandardButton.Yes)
        self.buttonBox.setCenterButtons(True)
        self.verticalLayout_3.addWidget(self.buttonBox)

        self.verticalLayout_2.addWidget(self.frame, 0, Qt.AlignmentFlag.AlignHCenter)
        self.verticalLayout.addLayout(self.verticalLayout_2)

        # Główny spacer dolny
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        self.verticalLayout.addItem(self.verticalSpacer)

        # Połączenie sygnałów akceptacji/odrzucenia okna
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
