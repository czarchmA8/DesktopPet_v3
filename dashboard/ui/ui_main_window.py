from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
        QAbstractItemView, QCheckBox, QComboBox,
        QFormLayout, QFrame, QGroupBox,
        QHBoxLayout, QLabel, QLineEdit, QListView,
        QListWidget, QMenuBar, QPushButton,
        QScrollArea, QSizePolicy, QSlider,
        QSpacerItem, QSplitter, QStatusBar,
        QTabWidget, QToolButton, QTreeWidget,
        QTreeWidgetItem, QVBoxLayout, QWidget,
        QMainWindow
)

from dashboard.widgets.aspect_ratio_label import AspectRatioLabel

class Ui_MainWindow(object):
    def setup_ui(self, MainWindow: QMainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QTabWidget(self.centralwidget)
        self.tabWidget.setObjectName("tabWidget")
        self.tab_settings = QWidget()
        self.tab_settings.setObjectName("tab_settings")
        self.verticalLayout_2 = QVBoxLayout(self.tab_settings)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.scrollArea = QScrollArea(self.tab_settings)
        self.scrollArea.setObjectName("scrollArea")
        self.scrollArea.setWidgetResizable(True)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.scrollAreaWidgetContents.setGeometry(QRect(0, 0, 341, 1136))
        self.verticalLayout_3 = QVBoxLayout(self.scrollAreaWidgetContents)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.groupBox_language = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_language.setObjectName("groupBox_language")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_language.sizePolicy().hasHeightForWidth())
        self.groupBox_language.setSizePolicy(sizePolicy)
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_language)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.comboBox_language = QComboBox(self.groupBox_language)
        self.comboBox_language.setObjectName("comboBox_language")

        self.verticalLayout_4.addWidget(self.comboBox_language)


        self.verticalLayout_3.addWidget(self.groupBox_language)

        self.groupBox_sound = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_sound.setObjectName("groupBox_sound")
        self.verticalLayout_8 = QVBoxLayout(self.groupBox_sound)
        self.verticalLayout_8.setObjectName("verticalLayout_8")
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName("horizontalLayout_7")
        self.label_volume = QLabel(self.groupBox_sound)
        self.label_volume.setObjectName("label_volume")

        self.horizontalLayout_7.addWidget(self.label_volume)

        self.horizontalSlider_volume = QSlider(self.groupBox_sound)
        self.horizontalSlider_volume.setObjectName("horizontalSlider_volume")
        self.horizontalSlider_volume.setMaximum(100)
        self.horizontalSlider_volume.setOrientation(Qt.Orientation.Horizontal)

        self.horizontalLayout_7.addWidget(self.horizontalSlider_volume)

        self.label_volume_percent = QLabel(self.groupBox_sound)
        self.label_volume_percent.setObjectName("label_volume_percent")
        self.label_volume_percent.setText("100%")

        self.horizontalLayout_7.addWidget(self.label_volume_percent)


        self.verticalLayout_8.addLayout(self.horizontalLayout_7)


        self.verticalLayout_3.addWidget(self.groupBox_sound)

        self.groupBox_app = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_app.setObjectName("groupBox_app")
        self.verticalLayout_7 = QVBoxLayout(self.groupBox_app)
        self.verticalLayout_7.setSpacing(6)
        self.verticalLayout_7.setObjectName("verticalLayout_7")
        self.frame_show = QFrame(self.groupBox_app)
        self.frame_show.setObjectName("frame_show")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.frame_show.sizePolicy().hasHeightForWidth())
        self.frame_show.setSizePolicy(sizePolicy1)
        self.frame_show.setStyleSheet("QFrame#frame_show {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_show.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_9 = QHBoxLayout(self.frame_show)
        self.horizontalLayout_9.setObjectName("horizontalLayout_9")
        self.horizontalLayout_9.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_9 = QVBoxLayout()
        self.verticalLayout_9.setSpacing(2)
        self.verticalLayout_9.setObjectName("verticalLayout_9")
        self.label_show_shortcut_title = QLabel(self.frame_show)
        self.label_show_shortcut_title.setObjectName("label_show_shortcut_title")
        self.label_show_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_9.addWidget(self.label_show_shortcut_title)

        self.label_show_shortcut_value = QLabel(self.frame_show)
        self.label_show_shortcut_value.setObjectName("label_show_shortcut_value")
        self.label_show_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_9.addWidget(self.label_show_shortcut_value)


        self.horizontalLayout_9.addLayout(self.verticalLayout_9)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_2)

        self.pushButton_show_shortcut_set = QPushButton(self.frame_show)
        self.pushButton_show_shortcut_set.setObjectName("pushButton_show_shortcut_set")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.pushButton_show_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_show_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_9.addWidget(self.pushButton_show_shortcut_set)

        self.pushButton_show_shortcut_remove = QPushButton(self.frame_show)
        self.pushButton_show_shortcut_remove.setObjectName("pushButton_show_shortcut_remove")
        self.pushButton_show_shortcut_remove.setEnabled(False)
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.pushButton_show_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_show_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_show_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_9.addWidget(self.pushButton_show_shortcut_remove)


        self.verticalLayout_7.addWidget(self.frame_show)

        self.frame_hide = QFrame(self.groupBox_app)
        self.frame_hide.setObjectName("frame_hide")
        sizePolicy1.setHeightForWidth(self.frame_hide.sizePolicy().hasHeightForWidth())
        self.frame_hide.setSizePolicy(sizePolicy1)
        self.frame_hide.setStyleSheet("QFrame#frame_hide {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_hide.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_2 = QHBoxLayout(self.frame_hide)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_10 = QVBoxLayout()
        self.verticalLayout_10.setSpacing(2)
        self.verticalLayout_10.setObjectName("verticalLayout_10")
        self.label_hide_shortcut_title = QLabel(self.frame_hide)
        self.label_hide_shortcut_title.setObjectName("label_hide_shortcut_title")
        self.label_hide_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_10.addWidget(self.label_hide_shortcut_title)

        self.label_hide_shortcut_value = QLabel(self.frame_hide)
        self.label_hide_shortcut_value.setObjectName("label_hide_shortcut_value")
        self.label_hide_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_10.addWidget(self.label_hide_shortcut_value)


        self.horizontalLayout_2.addLayout(self.verticalLayout_10)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer_3)

        self.pushButton_hide_shortcut_set = QPushButton(self.frame_hide)
        self.pushButton_hide_shortcut_set.setObjectName("pushButton_hide_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_hide_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_hide_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_2.addWidget(self.pushButton_hide_shortcut_set)

        self.pushButton_hide_shortcut_remove = QPushButton(self.frame_hide)
        self.pushButton_hide_shortcut_remove.setObjectName("pushButton_hide_shortcut_remove")
        self.pushButton_hide_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_hide_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_hide_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_hide_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_2.addWidget(self.pushButton_hide_shortcut_remove)


        self.verticalLayout_7.addWidget(self.frame_hide)

        self.frame_close = QFrame(self.groupBox_app)
        self.frame_close.setObjectName("frame_close")
        sizePolicy1.setHeightForWidth(self.frame_close.sizePolicy().hasHeightForWidth())
        self.frame_close.setSizePolicy(sizePolicy1)
        self.frame_close.setStyleSheet("QFrame#frame_close {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_close.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_8 = QHBoxLayout(self.frame_close)
        self.horizontalLayout_8.setObjectName("horizontalLayout_8")
        self.horizontalLayout_8.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_11 = QVBoxLayout()
        self.verticalLayout_11.setSpacing(2)
        self.verticalLayout_11.setObjectName("verticalLayout_11")
        self.label_close_shortcut_title = QLabel(self.frame_close)
        self.label_close_shortcut_title.setObjectName("label_close_shortcut_title")
        self.label_close_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_11.addWidget(self.label_close_shortcut_title)

        self.label_close_shortcut_value = QLabel(self.frame_close)
        self.label_close_shortcut_value.setObjectName("label_close_shortcut_value")
        self.label_close_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_11.addWidget(self.label_close_shortcut_value)


        self.horizontalLayout_8.addLayout(self.verticalLayout_11)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_4)

        self.pushButton_close_shortcut_set = QPushButton(self.frame_close)
        self.pushButton_close_shortcut_set.setObjectName("pushButton_close_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_close_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_close_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_8.addWidget(self.pushButton_close_shortcut_set)

        self.pushButton_close_shortcut_remove = QPushButton(self.frame_close)
        self.pushButton_close_shortcut_remove.setObjectName("pushButton_close_shortcut_remove")
        self.pushButton_close_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_close_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_close_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_close_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_8.addWidget(self.pushButton_close_shortcut_remove)


        self.verticalLayout_7.addWidget(self.frame_close)


        self.verticalLayout_3.addWidget(self.groupBox_app)

        self.groupBox_entities = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_entities.setObjectName("groupBox_entities")
        self.verticalLayout_12 = QVBoxLayout(self.groupBox_entities)
        self.verticalLayout_12.setObjectName("verticalLayout_12")
        self.frame_kill_all_entities_shortcut = QFrame(self.groupBox_entities)
        self.frame_kill_all_entities_shortcut.setObjectName("frame_kill_all_entities_shortcut")
        sizePolicy1.setHeightForWidth(self.frame_kill_all_entities_shortcut.sizePolicy().hasHeightForWidth())
        self.frame_kill_all_entities_shortcut.setSizePolicy(sizePolicy1)
        self.frame_kill_all_entities_shortcut.setStyleSheet("QFrame#frame_8 {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_kill_all_entities_shortcut.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_12 = QHBoxLayout(self.frame_kill_all_entities_shortcut)
        self.horizontalLayout_12.setObjectName("horizontalLayout_12")
        self.horizontalLayout_12.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_13 = QVBoxLayout()
        self.verticalLayout_13.setSpacing(2)
        self.verticalLayout_13.setObjectName("verticalLayout_13")
        self.label_kill_all_entities_shortcut_title = QLabel(self.frame_kill_all_entities_shortcut)
        self.label_kill_all_entities_shortcut_title.setObjectName("label_kill_all_entities_shortcut_title")
        self.label_kill_all_entities_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_13.addWidget(self.label_kill_all_entities_shortcut_title)

        self.label_kill_all_entities_shortcut_value = QLabel(self.frame_kill_all_entities_shortcut)
        self.label_kill_all_entities_shortcut_value.setObjectName("label_kill_all_entities_shortcut_value")
        self.label_kill_all_entities_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_13.addWidget(self.label_kill_all_entities_shortcut_value)


        self.horizontalLayout_12.addLayout(self.verticalLayout_13)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer_5)

        self.pushButton_kill_all_entities_shortcut_set = QPushButton(self.frame_kill_all_entities_shortcut)
        self.pushButton_kill_all_entities_shortcut_set.setObjectName("pushButton_kill_all_entities_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_kill_all_entities_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_kill_all_entities_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_12.addWidget(self.pushButton_kill_all_entities_shortcut_set)

        self.pushButton_kill_all_entities_shortcut_remove = QPushButton(self.frame_kill_all_entities_shortcut)
        self.pushButton_kill_all_entities_shortcut_remove.setObjectName("pushButton_kill_all_entities_shortcut_remove")
        self.pushButton_kill_all_entities_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_kill_all_entities_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_kill_all_entities_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_kill_all_entities_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_12.addWidget(self.pushButton_kill_all_entities_shortcut_remove)


        self.verticalLayout_12.addWidget(self.frame_kill_all_entities_shortcut)

        self.frame_show_all_entities_shortcut = QFrame(self.groupBox_entities)
        self.frame_show_all_entities_shortcut.setObjectName("frame_show_all_entities_shortcut")
        sizePolicy1.setHeightForWidth(self.frame_show_all_entities_shortcut.sizePolicy().hasHeightForWidth())
        self.frame_show_all_entities_shortcut.setSizePolicy(sizePolicy1)
        self.frame_show_all_entities_shortcut.setStyleSheet("QFrame#frame_delete_all {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_show_all_entities_shortcut.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_14 = QHBoxLayout(self.frame_show_all_entities_shortcut)
        self.horizontalLayout_14.setObjectName("horizontalLayout_14")
        self.horizontalLayout_14.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_28 = QVBoxLayout()
        self.verticalLayout_28.setSpacing(2)
        self.verticalLayout_28.setObjectName("verticalLayout_28")
        self.label_show_all_entities_shortcut_title = QLabel(self.frame_show_all_entities_shortcut)
        self.label_show_all_entities_shortcut_title.setObjectName("label_show_all_entities_shortcut_title")
        self.label_show_all_entities_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_28.addWidget(self.label_show_all_entities_shortcut_title)

        self.label_show_all_entities_shortcut_value = QLabel(self.frame_show_all_entities_shortcut)
        self.label_show_all_entities_shortcut_value.setObjectName("label_show_all_entities_shortcut_value")
        self.label_show_all_entities_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_28.addWidget(self.label_show_all_entities_shortcut_value)


        self.horizontalLayout_14.addLayout(self.verticalLayout_28)

        self.horizontalSpacer_9 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_9)

        self.pushButton_show_all_entities_shortcut_set = QPushButton(self.frame_show_all_entities_shortcut)
        self.pushButton_show_all_entities_shortcut_set.setObjectName("pushButton_show_all_entities_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_show_all_entities_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_show_all_entities_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_14.addWidget(self.pushButton_show_all_entities_shortcut_set)

        self.pushButton_show_all_entities_shortcut_remove = QPushButton(self.frame_show_all_entities_shortcut)
        self.pushButton_show_all_entities_shortcut_remove.setObjectName("pushButton_show_all_entities_shortcut_remove")
        self.pushButton_show_all_entities_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_show_all_entities_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_show_all_entities_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_show_all_entities_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_14.addWidget(self.pushButton_show_all_entities_shortcut_remove)


        self.verticalLayout_12.addWidget(self.frame_show_all_entities_shortcut)

        self.frame_hide_all_entities_shortcut = QFrame(self.groupBox_entities)
        self.frame_hide_all_entities_shortcut.setObjectName("frame_hide_all_entities_shortcut")
        sizePolicy1.setHeightForWidth(self.frame_hide_all_entities_shortcut.sizePolicy().hasHeightForWidth())
        self.frame_hide_all_entities_shortcut.setSizePolicy(sizePolicy1)
        self.frame_hide_all_entities_shortcut.setStyleSheet("QFrame#frame_delete_all {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_hide_all_entities_shortcut.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_16 = QHBoxLayout(self.frame_hide_all_entities_shortcut)
        self.horizontalLayout_16.setObjectName("horizontalLayout_16")
        self.horizontalLayout_16.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_30 = QVBoxLayout()
        self.verticalLayout_30.setSpacing(2)
        self.verticalLayout_30.setObjectName("verticalLayout_30")
        self.label_hide_all_entities_shortcut_title = QLabel(self.frame_hide_all_entities_shortcut)
        self.label_hide_all_entities_shortcut_title.setObjectName("label_hide_all_entities_shortcut_title")
        self.label_hide_all_entities_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_30.addWidget(self.label_hide_all_entities_shortcut_title)

        self.label_hide_all_entities_shortcut_value = QLabel(self.frame_hide_all_entities_shortcut)
        self.label_hide_all_entities_shortcut_value.setObjectName("label_hide_all_entities_shortcut_value")
        self.label_hide_all_entities_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_30.addWidget(self.label_hide_all_entities_shortcut_value)


        self.horizontalLayout_16.addLayout(self.verticalLayout_30)

        self.horizontalSpacer_11 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_16.addItem(self.horizontalSpacer_11)

        self.pushButton_hide_all_entities_shortcut_set = QPushButton(self.frame_hide_all_entities_shortcut)
        self.pushButton_hide_all_entities_shortcut_set.setObjectName("pushButton_hide_all_entities_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_hide_all_entities_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_hide_all_entities_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_16.addWidget(self.pushButton_hide_all_entities_shortcut_set)

        self.pushButton_hide_all_entities_shortcut_remove = QPushButton(self.frame_hide_all_entities_shortcut)
        self.pushButton_hide_all_entities_shortcut_remove.setObjectName("pushButton_hide_all_entities_shortcut_remove")
        self.pushButton_hide_all_entities_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_hide_all_entities_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_hide_all_entities_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_hide_all_entities_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_16.addWidget(self.pushButton_hide_all_entities_shortcut_remove)


        self.verticalLayout_12.addWidget(self.frame_hide_all_entities_shortcut)

        self.line = QFrame(self.groupBox_entities)
        self.line.setObjectName("line")
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_12.addWidget(self.line)

        self.frame_kill_selected_entity_shortcut = QFrame(self.groupBox_entities)
        self.frame_kill_selected_entity_shortcut.setObjectName("frame_kill_selected_entity_shortcut")
        sizePolicy1.setHeightForWidth(self.frame_kill_selected_entity_shortcut.sizePolicy().hasHeightForWidth())
        self.frame_kill_selected_entity_shortcut.setSizePolicy(sizePolicy1)
        self.frame_kill_selected_entity_shortcut.setStyleSheet("QFrame#frame_8 {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_kill_selected_entity_shortcut.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_15 = QHBoxLayout(self.frame_kill_selected_entity_shortcut)
        self.horizontalLayout_15.setObjectName("horizontalLayout_15")
        self.horizontalLayout_15.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_14 = QVBoxLayout()
        self.verticalLayout_14.setSpacing(2)
        self.verticalLayout_14.setObjectName("verticalLayout_14")
        self.label_kill_selected_entity_shortcut_title = QLabel(self.frame_kill_selected_entity_shortcut)
        self.label_kill_selected_entity_shortcut_title.setObjectName("label_kill_selected_entity_shortcut_title")
        self.label_kill_selected_entity_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_14.addWidget(self.label_kill_selected_entity_shortcut_title)

        self.label_kill_selected_entity_shortcut_value = QLabel(self.frame_kill_selected_entity_shortcut)
        self.label_kill_selected_entity_shortcut_value.setObjectName("label_kill_selected_entity_shortcut_value")
        self.label_kill_selected_entity_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_14.addWidget(self.label_kill_selected_entity_shortcut_value)


        self.horizontalLayout_15.addLayout(self.verticalLayout_14)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_6)

        self.pushButton_kill_selected_entity_shortcut_set = QPushButton(self.frame_kill_selected_entity_shortcut)
        self.pushButton_kill_selected_entity_shortcut_set.setObjectName("pushButton_kill_selected_entity_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_kill_selected_entity_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_kill_selected_entity_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_15.addWidget(self.pushButton_kill_selected_entity_shortcut_set)

        self.pushButton_kill_selected_entity_shortcut_remove = QPushButton(self.frame_kill_selected_entity_shortcut)
        self.pushButton_kill_selected_entity_shortcut_remove.setObjectName("pushButton_kill_selected_entity_shortcut_remove")
        self.pushButton_kill_selected_entity_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_kill_selected_entity_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_kill_selected_entity_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_kill_selected_entity_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_15.addWidget(self.pushButton_kill_selected_entity_shortcut_remove)


        self.verticalLayout_12.addWidget(self.frame_kill_selected_entity_shortcut)

        self.frame_show_selected_entity_shortcut = QFrame(self.groupBox_entities)
        self.frame_show_selected_entity_shortcut.setObjectName("frame_show_selected_entity_shortcut")
        sizePolicy1.setHeightForWidth(self.frame_show_selected_entity_shortcut.sizePolicy().hasHeightForWidth())
        self.frame_show_selected_entity_shortcut.setSizePolicy(sizePolicy1)
        self.frame_show_selected_entity_shortcut.setStyleSheet("QFrame#frame_delete_all {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_show_selected_entity_shortcut.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_18 = QHBoxLayout(self.frame_show_selected_entity_shortcut)
        self.horizontalLayout_18.setObjectName("horizontalLayout_18")
        self.horizontalLayout_18.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_32 = QVBoxLayout()
        self.verticalLayout_32.setSpacing(2)
        self.verticalLayout_32.setObjectName("verticalLayout_32")
        self.label_show_selected_entity_shortcut_title = QLabel(self.frame_show_selected_entity_shortcut)
        self.label_show_selected_entity_shortcut_title.setObjectName("label_show_selected_entity_shortcut_title")
        self.label_show_selected_entity_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_32.addWidget(self.label_show_selected_entity_shortcut_title)

        self.label_show_selected_entity_shortcut_value = QLabel(self.frame_show_selected_entity_shortcut)
        self.label_show_selected_entity_shortcut_value.setObjectName("label_show_selected_entity_shortcut_value")
        self.label_show_selected_entity_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_32.addWidget(self.label_show_selected_entity_shortcut_value)


        self.horizontalLayout_18.addLayout(self.verticalLayout_32)

        self.horizontalSpacer_13 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_18.addItem(self.horizontalSpacer_13)

        self.pushButton_show_selected_entity_shortcut_set = QPushButton(self.frame_show_selected_entity_shortcut)
        self.pushButton_show_selected_entity_shortcut_set.setObjectName("pushButton_show_selected_entity_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_show_selected_entity_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_show_selected_entity_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_18.addWidget(self.pushButton_show_selected_entity_shortcut_set)

        self.pushButton_show_selected_entity_shortcut_remove = QPushButton(self.frame_show_selected_entity_shortcut)
        self.pushButton_show_selected_entity_shortcut_remove.setObjectName("pushButton_show_selected_entity_shortcut_remove")
        self.pushButton_show_selected_entity_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_show_selected_entity_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_show_selected_entity_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_show_selected_entity_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_18.addWidget(self.pushButton_show_selected_entity_shortcut_remove)


        self.verticalLayout_12.addWidget(self.frame_show_selected_entity_shortcut)

        self.frame_hide_selected_entity_shortcut = QFrame(self.groupBox_entities)
        self.frame_hide_selected_entity_shortcut.setObjectName("frame_hide_selected_entity_shortcut")
        sizePolicy1.setHeightForWidth(self.frame_hide_selected_entity_shortcut.sizePolicy().hasHeightForWidth())
        self.frame_hide_selected_entity_shortcut.setSizePolicy(sizePolicy1)
        self.frame_hide_selected_entity_shortcut.setStyleSheet("QFrame#frame_delete_all {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_hide_selected_entity_shortcut.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_19 = QHBoxLayout(self.frame_hide_selected_entity_shortcut)
        self.horizontalLayout_19.setObjectName("horizontalLayout_19")
        self.horizontalLayout_19.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_33 = QVBoxLayout()
        self.verticalLayout_33.setSpacing(2)
        self.verticalLayout_33.setObjectName("verticalLayout_33")
        self.label_hide_selected_entity_shortcut_title = QLabel(self.frame_hide_selected_entity_shortcut)
        self.label_hide_selected_entity_shortcut_title.setObjectName("label_hide_selected_entity_shortcut_title")
        self.label_hide_selected_entity_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_33.addWidget(self.label_hide_selected_entity_shortcut_title)

        self.label_hide_selected_entity_shortcut_value = QLabel(self.frame_hide_selected_entity_shortcut)
        self.label_hide_selected_entity_shortcut_value.setObjectName("label_hide_selected_entity_shortcut_value")
        self.label_hide_selected_entity_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_33.addWidget(self.label_hide_selected_entity_shortcut_value)


        self.horizontalLayout_19.addLayout(self.verticalLayout_33)

        self.horizontalSpacer_14 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_19.addItem(self.horizontalSpacer_14)

        self.pushButton_hide_selected_entity_shortcut_set = QPushButton(self.frame_hide_selected_entity_shortcut)
        self.pushButton_hide_selected_entity_shortcut_set.setObjectName("pushButton_hide_selected_entity_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_hide_selected_entity_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_hide_selected_entity_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_19.addWidget(self.pushButton_hide_selected_entity_shortcut_set)

        self.pushButton_hide_selected_entity_shortcut_remove = QPushButton(self.frame_hide_selected_entity_shortcut)
        self.pushButton_hide_selected_entity_shortcut_remove.setObjectName("pushButton_hide_selected_entity_shortcut_remove")
        self.pushButton_hide_selected_entity_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_hide_selected_entity_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_hide_selected_entity_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_hide_selected_entity_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_19.addWidget(self.pushButton_hide_selected_entity_shortcut_remove)


        self.verticalLayout_12.addWidget(self.frame_hide_selected_entity_shortcut)

        self.frame_teleport_selected_entity_shortcut = QFrame(self.groupBox_entities)
        self.frame_teleport_selected_entity_shortcut.setObjectName("frame_teleport_selected_entity_shortcut")
        sizePolicy1.setHeightForWidth(self.frame_teleport_selected_entity_shortcut.sizePolicy().hasHeightForWidth())
        self.frame_teleport_selected_entity_shortcut.setSizePolicy(sizePolicy1)
        self.frame_teleport_selected_entity_shortcut.setStyleSheet("QFrame#frame_delete_all {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_teleport_selected_entity_shortcut.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_20 = QHBoxLayout(self.frame_teleport_selected_entity_shortcut)
        self.horizontalLayout_20.setObjectName("horizontalLayout_20")
        self.horizontalLayout_20.setContentsMargins(10, 8, 10, 8)
        self.verticalLayout_34 = QVBoxLayout()
        self.verticalLayout_34.setSpacing(2)
        self.verticalLayout_34.setObjectName("verticalLayout_34")
        self.label_teleport_selected_entity_shortcut_title = QLabel(self.frame_teleport_selected_entity_shortcut)
        self.label_teleport_selected_entity_shortcut_title.setObjectName("label_teleport_selected_entity_shortcut_title")
        self.label_teleport_selected_entity_shortcut_title.setStyleSheet("font-weight: 600;")

        self.verticalLayout_34.addWidget(self.label_teleport_selected_entity_shortcut_title)

        self.label_teleport_selected_entity_shortcut_value = QLabel(self.frame_teleport_selected_entity_shortcut)
        self.label_teleport_selected_entity_shortcut_value.setObjectName("label_teleport_selected_entity_shortcut_value")
        self.label_teleport_selected_entity_shortcut_value.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace; background-color: rgba(127, 127, 127, 40); border-radius: 4px; padding: 2px 8px;")

        self.verticalLayout_34.addWidget(self.label_teleport_selected_entity_shortcut_value)


        self.horizontalLayout_20.addLayout(self.verticalLayout_34)

        self.horizontalSpacer_15 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_20.addItem(self.horizontalSpacer_15)

        self.pushButton_teleport_selected_entity_shortcut_set = QPushButton(self.frame_teleport_selected_entity_shortcut)
        self.pushButton_teleport_selected_entity_shortcut_set.setObjectName("pushButton_teleport_selected_entity_shortcut_set")
        sizePolicy2.setHeightForWidth(self.pushButton_teleport_selected_entity_shortcut_set.sizePolicy().hasHeightForWidth())
        self.pushButton_teleport_selected_entity_shortcut_set.setSizePolicy(sizePolicy2)

        self.horizontalLayout_20.addWidget(self.pushButton_teleport_selected_entity_shortcut_set)

        self.pushButton_teleport_selected_entity_shortcut_remove = QPushButton(self.frame_teleport_selected_entity_shortcut)
        self.pushButton_teleport_selected_entity_shortcut_remove.setObjectName("pushButton_teleport_selected_entity_shortcut_remove")
        self.pushButton_teleport_selected_entity_shortcut_remove.setEnabled(False)
        sizePolicy3.setHeightForWidth(self.pushButton_teleport_selected_entity_shortcut_remove.sizePolicy().hasHeightForWidth())
        self.pushButton_teleport_selected_entity_shortcut_remove.setSizePolicy(sizePolicy3)
        self.pushButton_teleport_selected_entity_shortcut_remove.setMinimumSize(QSize(32, 0))

        self.horizontalLayout_20.addWidget(self.pushButton_teleport_selected_entity_shortcut_remove)


        self.verticalLayout_12.addWidget(self.frame_teleport_selected_entity_shortcut)

        self.line_2 = QFrame(self.groupBox_entities)
        self.line_2.setObjectName("line_2")
        self.line_2.setFrameShape(QFrame.Shape.HLine)
        self.line_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_12.addWidget(self.line_2)

        self.pushButton_open_objects_editor = QPushButton(self.groupBox_entities)
        self.pushButton_open_objects_editor.setObjectName("pushButton_open_objects_editor")

        self.verticalLayout_12.addWidget(self.pushButton_open_objects_editor)


        self.verticalLayout_3.addWidget(self.groupBox_entities)

        self.groupBox_system = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_system.setObjectName("groupBox_system")
        sizePolicy.setHeightForWidth(self.groupBox_system.sizePolicy().hasHeightForWidth())
        self.groupBox_system.setSizePolicy(sizePolicy)
        self.verticalLayout_5 = QVBoxLayout(self.groupBox_system)
        self.verticalLayout_5.setObjectName("verticalLayout_5")
        self.checkBox_check_for_updates = QCheckBox(self.groupBox_system)
        self.checkBox_check_for_updates.setObjectName("checkBox_check_for_updates")

        self.verticalLayout_5.addWidget(self.checkBox_check_for_updates)

        self.checkBox_autostart = QCheckBox(self.groupBox_system)
        self.checkBox_autostart.setObjectName("checkBox_autostart")
        self.checkBox_autostart.setEnabled(False)

        self.verticalLayout_5.addWidget(self.checkBox_autostart)


        self.verticalLayout_3.addWidget(self.groupBox_system)

        self.groupBox_advanced = QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_advanced.setObjectName("groupBox_advanced")
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_advanced)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.checkBox_debug_mode = QCheckBox(self.groupBox_advanced)
        self.checkBox_debug_mode.setObjectName("checkBox_debug_mode")

        self.verticalLayout_6.addWidget(self.checkBox_debug_mode)

        self.checkBox_hitboxes_overlay = QCheckBox(self.groupBox_advanced)
        self.checkBox_hitboxes_overlay.setObjectName("checkBox_hitboxes_overlay")
        self.checkBox_hitboxes_overlay.setEnabled(False)

        self.verticalLayout_6.addWidget(self.checkBox_hitboxes_overlay)

        self.checkBox_debug_information_window = QCheckBox(self.groupBox_advanced)
        self.checkBox_debug_information_window.setObjectName("checkBox_debug_information_window")
        self.checkBox_debug_information_window.setEnabled(False)

        self.verticalLayout_6.addWidget(self.checkBox_debug_information_window)


        self.verticalLayout_3.addWidget(self.groupBox_advanced)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_3)

        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.verticalLayout_2.addWidget(self.scrollArea)

        self.tabWidget.addTab(self.tab_settings, "")
        self.tab_mods = QWidget()
        self.tab_mods.setObjectName("tab_mods")
        self.verticalLayout_16 = QVBoxLayout(self.tab_mods)
        self.verticalLayout_16.setObjectName("verticalLayout_16")
        self.splitter = QSplitter(self.tab_mods)
        self.splitter.setObjectName("splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)
        self.groupBox_mods_list = QGroupBox(self.splitter)
        self.groupBox_mods_list.setObjectName("groupBox_mods_list")
        self.verticalLayout_17 = QVBoxLayout(self.groupBox_mods_list)
        self.verticalLayout_17.setObjectName("verticalLayout_17")
        self.listWidget_mods = QListWidget(self.groupBox_mods_list)
        self.listWidget_mods.setObjectName("listWidget_mods")
        self.listWidget_mods.setFrameShape(QFrame.Shape.NoFrame)
        self.listWidget_mods.setSpacing(2)
        self.listWidget_mods.setUniformItemSizes(True)

        self.verticalLayout_17.addWidget(self.listWidget_mods)

        self.splitter.addWidget(self.groupBox_mods_list)
        self.groupBox_mod_details = QGroupBox(self.splitter)
        self.groupBox_mod_details.setObjectName("groupBox_mod_details")
        self.verticalLayout_18 = QVBoxLayout(self.groupBox_mod_details)
        self.verticalLayout_18.setObjectName("verticalLayout_18")
        self.scrollArea_3 = QScrollArea(self.groupBox_mod_details)
        self.scrollArea_3.setObjectName("scrollArea_3")
        self.scrollArea_3.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea_3.setWidgetResizable(True)
        self.scrollAreaWidgetContents_3 = QWidget()
        self.scrollAreaWidgetContents_3.setObjectName("scrollAreaWidgetContents_3")
        self.scrollAreaWidgetContents_3.setGeometry(QRect(0, 0, 140, 406))
        self.verticalLayout_20 = QVBoxLayout(self.scrollAreaWidgetContents_3)
        self.verticalLayout_20.setSpacing(10)
        self.verticalLayout_20.setObjectName("verticalLayout_20")
        self.label_mod_preview = AspectRatioLabel(self.scrollAreaWidgetContents_3)
        self.label_mod_preview.setObjectName("label_mod_preview")
        self.label_mod_preview.setMinimumSize(QSize(0, 140))
        self.label_mod_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.label_mod_preview.setPixmap(QPixmap(":/images/no-preview.jpg"))
        self.label_mod_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_20.addWidget(self.label_mod_preview)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setSpacing(4)
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer)

        self.pushButton_mod_settings = QPushButton(self.scrollAreaWidgetContents_3)
        self.pushButton_mod_settings.setObjectName("pushButton_mod_settings")
        sizePolicy3.setHeightForWidth(self.pushButton_mod_settings.sizePolicy().hasHeightForWidth())
        self.pushButton_mod_settings.setSizePolicy(sizePolicy3)
        self.pushButton_mod_settings.setMinimumSize(QSize(32, 28))
        self.pushButton_mod_settings.setMaximumSize(QSize(32, 28))
        self.pushButton_mod_settings.setText("⚙️")

        self.horizontalLayout_5.addWidget(self.pushButton_mod_settings)

        self.toolButton_mod_browse = QToolButton(self.scrollAreaWidgetContents_3)
        self.toolButton_mod_browse.setObjectName("toolButton_mod_browse")
        self.toolButton_mod_browse.setText("...")

        self.horizontalLayout_5.addWidget(self.toolButton_mod_browse)


        self.verticalLayout_20.addLayout(self.horizontalLayout_5)

        self.frame_mod_info = QFrame(self.scrollAreaWidgetContents_3)
        self.frame_mod_info.setObjectName("frame_mod_info")
        self.frame_mod_info.setStyleSheet("QFrame#frame_mod_info {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_mod_info.setFrameShape(QFrame.Shape.StyledPanel)
        self.formLayout_mod_info = QFormLayout(self.frame_mod_info)
        self.formLayout_mod_info.setObjectName("formLayout_mod_info")
        self.formLayout_mod_info.setHorizontalSpacing(8)
        self.formLayout_mod_info.setVerticalSpacing(4)
        self.formLayout_mod_info.setContentsMargins(10, 8, 10, 8)
        self.label_mod_name = QLabel(self.frame_mod_info)
        self.label_mod_name.setObjectName("label_mod_name")
        font = QFont()
        font.setPointSize(12)
        font.setBold(True)
        self.label_mod_name.setFont(font)
        self.label_mod_name.setText("ModName")

        self.formLayout_mod_info.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.label_mod_name)

        self.line_mod_info_sep = QFrame(self.frame_mod_info)
        self.line_mod_info_sep.setObjectName("line_mod_info_sep")
        self.line_mod_info_sep.setFrameShape(QFrame.Shape.HLine)
        self.line_mod_info_sep.setFrameShadow(QFrame.Shadow.Sunken)

        self.formLayout_mod_info.setWidget(1, QFormLayout.ItemRole.SpanningRole, self.line_mod_info_sep)

        self.label_mod_author_title = QLabel(self.frame_mod_info)
        self.label_mod_author_title.setObjectName("label_mod_author_title")
        self.label_mod_author_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_mod_author_title)

        self.label_mod_author = QLabel(self.frame_mod_info)
        self.label_mod_author.setObjectName("label_mod_author")
        self.label_mod_author.setText("unknown")

        self.formLayout_mod_info.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_mod_author)

        self.label_mod_version_title = QLabel(self.frame_mod_info)
        self.label_mod_version_title.setObjectName("label_mod_version_title")
        self.label_mod_version_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_mod_version_title)

        self.label_mod_version = QLabel(self.frame_mod_info)
        self.label_mod_version.setObjectName("label_mod_version")
        self.label_mod_version.setText("unknown")

        self.formLayout_mod_info.setWidget(3, QFormLayout.ItemRole.FieldRole, self.label_mod_version)

        self.label_mod_id_title = QLabel(self.frame_mod_info)
        self.label_mod_id_title.setObjectName("label_mod_id_title")
        self.label_mod_id_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_mod_id_title)

        self.label_mod_id = QLabel(self.frame_mod_info)
        self.label_mod_id.setObjectName("label_mod_id")
        self.label_mod_id.setText("unknown")

        self.formLayout_mod_info.setWidget(4, QFormLayout.ItemRole.FieldRole, self.label_mod_id)


        self.verticalLayout_20.addWidget(self.frame_mod_info)

        self.label_mod_description = QLabel(self.scrollAreaWidgetContents_3)
        self.label_mod_description.setObjectName("label_mod_description")
        self.label_mod_description.setWordWrap(True)

        self.verticalLayout_20.addWidget(self.label_mod_description)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_20.addItem(self.verticalSpacer)

        self.scrollArea_3.setWidget(self.scrollAreaWidgetContents_3)

        self.verticalLayout_18.addWidget(self.scrollArea_3)

        self.splitter.addWidget(self.groupBox_mod_details)

        self.verticalLayout_16.addWidget(self.splitter)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.pushButton_load_mod_list = QPushButton(self.tab_mods)
        self.pushButton_load_mod_list.setObjectName("pushButton_load_mod_list")

        self.horizontalLayout_4.addWidget(self.pushButton_load_mod_list)

        self.pushButton_save_mod_list = QPushButton(self.tab_mods)
        self.pushButton_save_mod_list.setObjectName("pushButton_save_mod_list")

        self.horizontalLayout_4.addWidget(self.pushButton_save_mod_list)

        self.pushButton_discard_mod_changes = QPushButton(self.tab_mods)
        self.pushButton_discard_mod_changes.setObjectName("pushButton_discard_mod_changes")
        self.pushButton_discard_mod_changes.setEnabled(False)

        self.horizontalLayout_4.addWidget(self.pushButton_discard_mod_changes)

        self.pushButton_save_mod_changes = QPushButton(self.tab_mods)
        self.pushButton_save_mod_changes.setObjectName("pushButton_save_mod_changes")
        self.pushButton_save_mod_changes.setEnabled(False)

        self.horizontalLayout_4.addWidget(self.pushButton_save_mod_changes)


        self.verticalLayout_16.addLayout(self.horizontalLayout_4)

        self.tabWidget.addTab(self.tab_mods, "")
        self.tab_list = QWidget()
        self.tab_list.setObjectName("tab_list")
        self.verticalLayout_23 = QVBoxLayout(self.tab_list)
        self.verticalLayout_23.setObjectName("verticalLayout_23")
        self.splitter_2 = QSplitter(self.tab_list)
        self.splitter_2.setObjectName("splitter_2")
        self.splitter_2.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_2.setChildrenCollapsible(False)
        self.groupBox_entities_list = QGroupBox(self.splitter_2)
        self.groupBox_entities_list.setObjectName("groupBox_entities_list")
        self.verticalLayout_24 = QVBoxLayout(self.groupBox_entities_list)
        self.verticalLayout_24.setObjectName("verticalLayout_24")
        self.lineEdit_entity_search = QLineEdit(self.groupBox_entities_list)
        self.lineEdit_entity_search.setObjectName("lineEdit_entity_search")
        self.lineEdit_entity_search.setClearButtonEnabled(True)

        self.verticalLayout_24.addWidget(self.lineEdit_entity_search)

        self.listWidget_entities_list = QListWidget(self.groupBox_entities_list)
        self.listWidget_entities_list.setObjectName("listWidget_entities_list")
        self.listWidget_entities_list.setFrameShape(QFrame.Shape.NoFrame)
        self.listWidget_entities_list.setSpacing(2)
        self.listWidget_entities_list.setUniformItemSizes(True)

        self.verticalLayout_24.addWidget(self.listWidget_entities_list)

        self.splitter_2.addWidget(self.groupBox_entities_list)
        self.groupBox_entity_details = QGroupBox(self.splitter_2)
        self.groupBox_entity_details.setObjectName("groupBox_entity_details")
        self.verticalLayout_25 = QVBoxLayout(self.groupBox_entity_details)
        self.verticalLayout_25.setObjectName("verticalLayout_25")
        self.scrollArea_4 = QScrollArea(self.groupBox_entity_details)
        self.scrollArea_4.setObjectName("scrollArea_4")
        self.scrollArea_4.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea_4.setWidgetResizable(True)
        self.scrollAreaWidgetContents_4 = QWidget()
        self.scrollAreaWidgetContents_4.setObjectName("scrollAreaWidgetContents_4")
        self.scrollAreaWidgetContents_4.setGeometry(QRect(0, 0, 159, 498))
        self.verticalLayout_26 = QVBoxLayout(self.scrollAreaWidgetContents_4)
        self.verticalLayout_26.setSpacing(10)
        self.verticalLayout_26.setObjectName("verticalLayout_26")
        self.label_entity_preview = AspectRatioLabel(self.scrollAreaWidgetContents_4)
        self.label_entity_preview.setObjectName("label_entity_preview")
        self.label_entity_preview.setMinimumSize(QSize(0, 140))
        self.label_entity_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.label_entity_preview.setPixmap(QPixmap(":/images/no-preview.jpg"))
        self.label_entity_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_26.addWidget(self.label_entity_preview)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setSpacing(4)
        self.horizontalLayout_11.setObjectName("horizontalLayout_11")
        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_11.addItem(self.horizontalSpacer_7)

        self.pushButton_entity_settings = QPushButton(self.scrollAreaWidgetContents_4)
        self.pushButton_entity_settings.setObjectName("pushButton_entity_settings")
        sizePolicy3.setHeightForWidth(self.pushButton_entity_settings.sizePolicy().hasHeightForWidth())
        self.pushButton_entity_settings.setSizePolicy(sizePolicy3)
        self.pushButton_entity_settings.setMinimumSize(QSize(32, 28))
        self.pushButton_entity_settings.setMaximumSize(QSize(32, 28))
        self.pushButton_entity_settings.setText("⚙️")

        self.horizontalLayout_11.addWidget(self.pushButton_entity_settings)

        self.toolButton_entity_browse = QToolButton(self.scrollAreaWidgetContents_4)
        self.toolButton_entity_browse.setObjectName("toolButton_entity_browse")
        self.toolButton_entity_browse.setText("...")

        self.horizontalLayout_11.addWidget(self.toolButton_entity_browse)


        self.verticalLayout_26.addLayout(self.horizontalLayout_11)

        self.frame_entity_info = QFrame(self.scrollAreaWidgetContents_4)
        self.frame_entity_info.setObjectName("frame_entity_info")
        self.frame_entity_info.setStyleSheet("QFrame#frame_mod_info {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_entity_info.setFrameShape(QFrame.Shape.StyledPanel)
        self.formLayout_mod_info_2 = QFormLayout(self.frame_entity_info)
        self.formLayout_mod_info_2.setObjectName("formLayout_mod_info_2")
        self.formLayout_mod_info_2.setHorizontalSpacing(8)
        self.formLayout_mod_info_2.setVerticalSpacing(4)
        self.formLayout_mod_info_2.setContentsMargins(10, 8, 10, 8)
        self.label_entity_name = QLabel(self.frame_entity_info)
        self.label_entity_name.setObjectName("label_entity_name")
        self.label_entity_name.setFont(font)
        self.label_entity_name.setText("EntityName")

        self.formLayout_mod_info_2.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.label_entity_name)

        self.line_mod_info_sep_2 = QFrame(self.frame_entity_info)
        self.line_mod_info_sep_2.setObjectName("line_mod_info_sep_2")
        self.line_mod_info_sep_2.setFrameShape(QFrame.Shape.HLine)
        self.line_mod_info_sep_2.setFrameShadow(QFrame.Shadow.Sunken)

        self.formLayout_mod_info_2.setWidget(1, QFormLayout.ItemRole.SpanningRole, self.line_mod_info_sep_2)

        self.label_entity_mod_name_title = QLabel(self.frame_entity_info)
        self.label_entity_mod_name_title.setObjectName("label_entity_mod_name_title")
        self.label_entity_mod_name_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_entity_mod_name_title)

        self.label_entity_mod_name = QLabel(self.frame_entity_info)
        self.label_entity_mod_name.setObjectName("label_entity_mod_name")
        self.label_entity_mod_name.setText("unknown")

        self.formLayout_mod_info_2.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_entity_mod_name)

        self.label_entity_mod_id_title = QLabel(self.frame_entity_info)
        self.label_entity_mod_id_title.setObjectName("label_entity_mod_id_title")
        self.label_entity_mod_id_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_2.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_entity_mod_id_title)

        self.label_entity_mod_id = QLabel(self.frame_entity_info)
        self.label_entity_mod_id.setObjectName("label_entity_mod_id")
        self.label_entity_mod_id.setText("unknown")

        self.formLayout_mod_info_2.setWidget(3, QFormLayout.ItemRole.FieldRole, self.label_entity_mod_id)

        self.label_entity_id_title = QLabel(self.frame_entity_info)
        self.label_entity_id_title.setObjectName("label_entity_id_title")
        self.label_entity_id_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_2.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_entity_id_title)

        self.label_entity_id = QLabel(self.frame_entity_info)
        self.label_entity_id.setObjectName("label_entity_id")
        self.label_entity_id.setText("unknown")

        self.formLayout_mod_info_2.setWidget(4, QFormLayout.ItemRole.FieldRole, self.label_entity_id)


        self.verticalLayout_26.addWidget(self.frame_entity_info)

        self.label_entity_description = QLabel(self.scrollAreaWidgetContents_4)
        self.label_entity_description.setObjectName("label_entity_description")
        self.label_entity_description.setWordWrap(True)

        self.verticalLayout_26.addWidget(self.label_entity_description)

        self.frame_entity_debug = QFrame(self.scrollAreaWidgetContents_4)
        self.frame_entity_debug.setObjectName("frame_entity_debug")
        self.frame_entity_debug.setStyleSheet("QFrame#frame_mod_info {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_entity_debug.setFrameShape(QFrame.Shape.StyledPanel)
        self.formLayout_mod_info_4 = QFormLayout(self.frame_entity_debug)
        self.formLayout_mod_info_4.setObjectName("formLayout_mod_info_4")
        self.formLayout_mod_info_4.setHorizontalSpacing(8)
        self.formLayout_mod_info_4.setVerticalSpacing(4)
        self.formLayout_mod_info_4.setContentsMargins(10, 8, 10, 8)
        self.label_entity_position_title = QLabel(self.frame_entity_debug)
        self.label_entity_position_title.setObjectName("label_entity_position_title")
        self.label_entity_position_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_4.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_entity_position_title)

        self.label_entity_position = QLabel(self.frame_entity_debug)
        self.label_entity_position.setText("x: 0, y: 0")
        self.label_entity_position.setObjectName("label_entity_position")

        self.formLayout_mod_info_4.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_entity_position)

        self.label_entity_rotation_title = QLabel(self.frame_entity_debug)
        self.label_entity_rotation_title.setObjectName("label_entity_rotation_title")
        self.label_entity_rotation_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_4.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_entity_rotation_title)

        self.label_entity_rotation = QLabel(self.frame_entity_debug)
        self.label_entity_rotation.setText("0")
        self.label_entity_rotation.setObjectName("label_entity_rotation")

        self.formLayout_mod_info_4.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_entity_rotation)

        self.label_entity_velocity_title = QLabel(self.frame_entity_debug)
        self.label_entity_velocity_title.setObjectName("label_entity_velocity_title")
        self.label_entity_velocity_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_4.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_entity_velocity_title)

        self.label_entity_velocity = QLabel(self.frame_entity_debug)
        self.label_entity_velocity.setText("x: 0, y: 0")
        self.label_entity_velocity.setObjectName("label_entity_velocity")

        self.formLayout_mod_info_4.setWidget(3, QFormLayout.ItemRole.FieldRole, self.label_entity_velocity)

        self.label_entity_hwnd_title = QLabel(self.frame_entity_debug)
        self.label_entity_hwnd_title.setObjectName("label_entity_hwnd_title")
        self.label_entity_hwnd_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_4.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_entity_hwnd_title)

        self.label_entity_hwnd = QLabel(self.frame_entity_debug)
        self.label_entity_hwnd.setObjectName("label_entity_hwnd")

        self.formLayout_mod_info_4.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_entity_hwnd)


        self.verticalLayout_26.addWidget(self.frame_entity_debug)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_26.addItem(self.verticalSpacer_4)

        self.scrollArea_4.setWidget(self.scrollAreaWidgetContents_4)

        self.verticalLayout_25.addWidget(self.scrollArea_4)

        self.splitter_2.addWidget(self.groupBox_entity_details)

        self.verticalLayout_23.addWidget(self.splitter_2)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName("horizontalLayout_6")
        self.pushButton_kill_all_entities = QPushButton(self.tab_list)
        self.pushButton_kill_all_entities.setObjectName("pushButton_kill_all_entities")

        self.horizontalLayout_6.addWidget(self.pushButton_kill_all_entities)

        self.pushButton_show_all_entities = QPushButton(self.tab_list)
        self.pushButton_show_all_entities.setObjectName("pushButton_show_all_entities")

        self.horizontalLayout_6.addWidget(self.pushButton_show_all_entities)

        self.pushButton_hide_all_entities = QPushButton(self.tab_list)
        self.pushButton_hide_all_entities.setObjectName("pushButton_hide_all_entities")

        self.horizontalLayout_6.addWidget(self.pushButton_hide_all_entities)


        self.verticalLayout_23.addLayout(self.horizontalLayout_6)

        self.tabWidget.addTab(self.tab_list, "")
        self.tab_add = QWidget()
        self.tab_add.setObjectName("tab_add")
        self.verticalLayout_21 = QVBoxLayout(self.tab_add)
        self.verticalLayout_21.setObjectName("verticalLayout_21")
        self.splitter_add = QSplitter(self.tab_add)
        self.splitter_add.setObjectName("splitter_add")
        self.splitter_add.setOrientation(Qt.Orientation.Horizontal)
        self.splitter_add.setHandleWidth(4)
        self.splitter_add.setChildrenCollapsible(False)
        self.treeWidget_add_categories = QTreeWidget(self.splitter_add)
        QTreeWidgetItem(self.treeWidget_add_categories)
        QTreeWidgetItem(self.treeWidget_add_categories)
        QTreeWidgetItem(self.treeWidget_add_categories)
        self.treeWidget_add_categories.setObjectName("treeWidget_add_categories")
        self.treeWidget_add_categories.setMinimumSize(QSize(170, 0))
        self.treeWidget_add_categories.setMaximumSize(QSize(240, 16777215))
        self.treeWidget_add_categories.setFrameShape(QFrame.Shape.NoFrame)
        self.treeWidget_add_categories.setIndentation(14)
        self.treeWidget_add_categories.setAnimated(True)
        self.treeWidget_add_categories.setHeaderHidden(True)
        self.splitter_add.addWidget(self.treeWidget_add_categories)
        self.groupBox_add_entities = QGroupBox(self.splitter_add)
        self.groupBox_add_entities.setObjectName("groupBox_add_entities")
        sizePolicy4 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy4.setHorizontalStretch(1)
        sizePolicy4.setVerticalStretch(0)
        sizePolicy4.setHeightForWidth(self.groupBox_add_entities.sizePolicy().hasHeightForWidth())
        self.groupBox_add_entities.setSizePolicy(sizePolicy4)
        self.verticalLayout_add_objects_2 = QVBoxLayout(self.groupBox_add_entities)
        self.verticalLayout_add_objects_2.setObjectName("verticalLayout_add_objects_2")
        self.lineEdit_add_search = QLineEdit(self.groupBox_add_entities)
        self.lineEdit_add_search.setObjectName("lineEdit_add_search")
        self.lineEdit_add_search.setClearButtonEnabled(True)

        self.verticalLayout_add_objects_2.addWidget(self.lineEdit_add_search)

        self.listWidget_add_entities_list = QListWidget(self.groupBox_add_entities)
        self.listWidget_add_entities_list.setObjectName("listWidget_add_entities_list")
        self.listWidget_add_entities_list.setFrameShape(QFrame.Shape.NoFrame)
        self.listWidget_add_entities_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.listWidget_add_entities_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.listWidget_add_entities_list.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.listWidget_add_entities_list.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.listWidget_add_entities_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.listWidget_add_entities_list.setIconSize(QSize(64, 64))
        self.listWidget_add_entities_list.setMovement(QListView.Movement.Static)
        self.listWidget_add_entities_list.setFlow(QListView.Flow.LeftToRight)
        self.listWidget_add_entities_list.setResizeMode(QListView.ResizeMode.Adjust)
        self.listWidget_add_entities_list.setGridSize(QSize(88, 96))
        self.listWidget_add_entities_list.setViewMode(QListView.ViewMode.IconMode)
        self.listWidget_add_entities_list.setUniformItemSizes(True)
        self.listWidget_add_entities_list.setWordWrap(True)

        self.verticalLayout_add_objects_2.addWidget(self.listWidget_add_entities_list)

        self.splitter_add.addWidget(self.groupBox_add_entities)
        self.groupBox_add_entity_details = QGroupBox(self.splitter_add)
        self.groupBox_add_entity_details.setObjectName("groupBox_add_entity_details")
        self.groupBox_add_entity_details.setMinimumSize(QSize(230, 0))
        self.groupBox_add_entity_details.setMaximumSize(QSize(300, 16777215))
        self.verticalLayout_add_object_details_2 = QVBoxLayout(self.groupBox_add_entity_details)
        self.verticalLayout_add_object_details_2.setObjectName("verticalLayout_add_object_details_2")
        self.scrollArea_5 = QScrollArea(self.groupBox_add_entity_details)
        self.scrollArea_5.setObjectName("scrollArea_5")
        self.scrollArea_5.setFrameShape(QFrame.Shape.NoFrame)
        self.scrollArea_5.setWidgetResizable(True)
        self.scrollAreaWidgetContents_5 = QWidget()
        self.scrollAreaWidgetContents_5.setObjectName("scrollAreaWidgetContents_5")
        self.scrollAreaWidgetContents_5.setGeometry(QRect(0, 0, 159, 428))
        self.verticalLayout_27 = QVBoxLayout(self.scrollAreaWidgetContents_5)
        self.verticalLayout_27.setSpacing(10)
        self.verticalLayout_27.setObjectName("verticalLayout_27")
        self.label_add_entity_preview = AspectRatioLabel(self.scrollAreaWidgetContents_5)
        self.label_add_entity_preview.setObjectName("label_add_entity_preview")
        self.label_add_entity_preview.setMinimumSize(QSize(0, 140))
        self.label_add_entity_preview.setFrameShape(QFrame.Shape.StyledPanel)
        self.label_add_entity_preview.setPixmap(QPixmap(":/images/no-preview.jpg"))
        self.label_add_entity_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_27.addWidget(self.label_add_entity_preview)

        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setSpacing(4)
        self.horizontalLayout_13.setObjectName("horizontalLayout_13")
        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_13.addItem(self.horizontalSpacer_8)

        self.pushButton_add_entity_settings = QPushButton(self.scrollAreaWidgetContents_5)
        self.pushButton_add_entity_settings.setObjectName("pushButton_add_entity_settings")
        sizePolicy3.setHeightForWidth(self.pushButton_add_entity_settings.sizePolicy().hasHeightForWidth())
        self.pushButton_add_entity_settings.setSizePolicy(sizePolicy3)
        self.pushButton_add_entity_settings.setMinimumSize(QSize(32, 28))
        self.pushButton_add_entity_settings.setMaximumSize(QSize(32, 28))
        self.pushButton_add_entity_settings.setText("⚙️")

        self.horizontalLayout_13.addWidget(self.pushButton_add_entity_settings)

        self.toolButton_add_entity_browse = QToolButton(self.scrollAreaWidgetContents_5)
        self.toolButton_add_entity_browse.setObjectName("toolButton_add_entity_browse")
        self.toolButton_add_entity_browse.setText("...")

        self.horizontalLayout_13.addWidget(self.toolButton_add_entity_browse)


        self.verticalLayout_27.addLayout(self.horizontalLayout_13)

        self.frame_add_entity_info = QFrame(self.scrollAreaWidgetContents_5)
        self.frame_add_entity_info.setObjectName("frame_add_entity_info")
        self.frame_add_entity_info.setStyleSheet("QFrame#frame_mod_info {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_add_entity_info.setFrameShape(QFrame.Shape.StyledPanel)
        self.formLayout_mod_info_3 = QFormLayout(self.frame_add_entity_info)
        self.formLayout_mod_info_3.setObjectName("formLayout_mod_info_3")
        self.formLayout_mod_info_3.setHorizontalSpacing(8)
        self.formLayout_mod_info_3.setVerticalSpacing(4)
        self.formLayout_mod_info_3.setContentsMargins(10, 8, 10, 8)
        self.label_add_entity_name = QLabel(self.frame_add_entity_info)
        self.label_add_entity_name.setObjectName("label_add_entity_name")
        self.label_add_entity_name.setFont(font)
        self.label_add_entity_name.setText("EntityName")

        self.formLayout_mod_info_3.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.label_add_entity_name)

        self.line_mod_info_sep_3 = QFrame(self.frame_add_entity_info)
        self.line_mod_info_sep_3.setObjectName("line_mod_info_sep_3")
        self.line_mod_info_sep_3.setFrameShape(QFrame.Shape.HLine)
        self.line_mod_info_sep_3.setFrameShadow(QFrame.Shadow.Sunken)

        self.formLayout_mod_info_3.setWidget(1, QFormLayout.ItemRole.SpanningRole, self.line_mod_info_sep_3)

        self.label_add_entity_mod_name_title = QLabel(self.frame_add_entity_info)
        self.label_add_entity_mod_name_title.setObjectName("label_add_entity_mod_name_title")
        self.label_add_entity_mod_name_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_3.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_add_entity_mod_name_title)

        self.label_add_entity_mod_name = QLabel(self.frame_add_entity_info)
        self.label_add_entity_mod_name.setObjectName("label_add_entity_mod_name")
        self.label_add_entity_mod_name.setText("unknown")

        self.formLayout_mod_info_3.setWidget(2, QFormLayout.ItemRole.FieldRole, self.label_add_entity_mod_name)

        self.label_add_entity_mod_id_title = QLabel(self.frame_add_entity_info)
        self.label_add_entity_mod_id_title.setObjectName("label_add_entity_mod_id_title")
        self.label_add_entity_mod_id_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_3.setWidget(3, QFormLayout.ItemRole.LabelRole, self.label_add_entity_mod_id_title)

        self.label_add_entity_mod_id = QLabel(self.frame_add_entity_info)
        self.label_add_entity_mod_id.setObjectName("label_add_entity_mod_id")
        self.label_add_entity_mod_id.setText("unknown")

        self.formLayout_mod_info_3.setWidget(3, QFormLayout.ItemRole.FieldRole, self.label_add_entity_mod_id)

        self.label_add_entity_id_title = QLabel(self.frame_add_entity_info)
        self.label_add_entity_id_title.setObjectName("label_add_entity_id_title")
        self.label_add_entity_id_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_mod_info_3.setWidget(4, QFormLayout.ItemRole.LabelRole, self.label_add_entity_id_title)

        self.label_add_entity_id = QLabel(self.frame_add_entity_info)
        self.label_add_entity_id.setObjectName("label_add_entity_id")
        self.label_add_entity_id.setText("unknown")

        self.formLayout_mod_info_3.setWidget(4, QFormLayout.ItemRole.FieldRole, self.label_add_entity_id)


        self.verticalLayout_27.addWidget(self.frame_add_entity_info)

        self.pushButton_add_entity = QPushButton(self.scrollAreaWidgetContents_5)
        self.pushButton_add_entity.setObjectName("pushButton_add_entity")

        self.verticalLayout_27.addWidget(self.pushButton_add_entity)

        self.label_add_entity_description = QLabel(self.scrollAreaWidgetContents_5)
        self.label_add_entity_description.setObjectName("label_add_entity_description")
        self.label_add_entity_description.setWordWrap(True)

        self.verticalLayout_27.addWidget(self.label_add_entity_description)

        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_27.addItem(self.verticalSpacer_5)

        self.scrollArea_5.setWidget(self.scrollAreaWidgetContents_5)

        self.verticalLayout_add_object_details_2.addWidget(self.scrollArea_5)

        self.splitter_add.addWidget(self.groupBox_add_entity_details)

        self.verticalLayout_21.addWidget(self.splitter_add)

        self.tabWidget.addTab(self.tab_add, "")
        self.tab_info = QWidget()
        self.tab_info.setObjectName("tab_info")
        self.verticalLayout_19 = QVBoxLayout(self.tab_info)
        self.verticalLayout_19.setObjectName("verticalLayout_19")
        self.scrollArea_2 = QScrollArea(self.tab_info)
        self.scrollArea_2.setObjectName("scrollArea_2")
        self.scrollArea_2.setWidgetResizable(True)
        self.scrollAreaWidgetContents_2 = QWidget()
        self.scrollAreaWidgetContents_2.setObjectName("scrollAreaWidgetContents_2")
        self.scrollAreaWidgetContents_2.setGeometry(QRect(0, 0, 754, 450))
        self.verticalLayout_22 = QVBoxLayout(self.scrollAreaWidgetContents_2)
        self.verticalLayout_22.setObjectName("verticalLayout_22")
        self.label_app_banner = AspectRatioLabel(self.scrollAreaWidgetContents_2)
        self.label_app_banner.setObjectName("label_app_banner")
        self.label_app_banner.setStyleSheet("font-size: 40px;")
        self.label_app_banner.setFrameShape(QFrame.Shape.StyledPanel)
        self.label_app_banner.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_22.addWidget(self.label_app_banner)

        self.label_app_name = QLabel(self.scrollAreaWidgetContents_2)
        self.label_app_name.setObjectName("label_app_name")
        self.label_app_name.setStyleSheet("font-size: 18px; font-weight: 600;")
        self.label_app_name.setText("DesktopPet v3")
        self.label_app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_22.addWidget(self.label_app_name)

        self.label_app_version = QLabel(self.scrollAreaWidgetContents_2)
        self.label_app_version.setObjectName("label_app_version")
        self.label_app_version.setStyleSheet("color: #aaa; font-family: monospace; padding: 1px 8px;")
        self.label_app_version.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.verticalLayout_22.addWidget(self.label_app_version)

        self.label_app_description = QLabel(self.scrollAreaWidgetContents_2)
        self.label_app_description.setObjectName("label_app_description")
        self.label_app_description.setStyleSheet("color: #ccc;")
        self.label_app_description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label_app_description.setWordWrap(True)
        self.label_app_description.setMargin(4)

        self.verticalLayout_22.addWidget(self.label_app_description)

        self.line_info_sep_top = QFrame(self.scrollAreaWidgetContents_2)
        self.line_info_sep_top.setObjectName("line_info_sep_top")
        self.line_info_sep_top.setFrameShape(QFrame.Shape.HLine)
        self.line_info_sep_top.setFrameShadow(QFrame.Shadow.Sunken)

        self.verticalLayout_22.addWidget(self.line_info_sep_top)

        self.frame_app_details = QFrame(self.scrollAreaWidgetContents_2)
        self.frame_app_details.setObjectName("frame_app_details")
        self.frame_app_details.setStyleSheet("QFrame#frame_app_details {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_app_details.setFrameShape(QFrame.Shape.StyledPanel)
        self.formLayout_app_details = QFormLayout(self.frame_app_details)
        self.formLayout_app_details.setObjectName("formLayout_app_details")
        self.formLayout_app_details.setHorizontalSpacing(8)
        self.formLayout_app_details.setVerticalSpacing(6)
        self.formLayout_app_details.setContentsMargins(12, 10, 12, 10)
        self.label_app_author_title = QLabel(self.frame_app_details)
        self.label_app_author_title.setObjectName("label_app_author_title")
        self.label_app_author_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_app_details.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label_app_author_title)

        self.label_app_author = QLabel(self.frame_app_details)
        self.label_app_author.setObjectName("label_app_author")
        self.label_app_author.setText("czarchmA8")

        self.formLayout_app_details.setWidget(0, QFormLayout.ItemRole.FieldRole, self.label_app_author)

        self.label_app_repository_title = QLabel(self.frame_app_details)
        self.label_app_repository_title.setObjectName("label_app_repository_title")
        self.label_app_repository_title.setStyleSheet("color: #aaa; font-style: italic;")

        self.formLayout_app_details.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_app_repository_title)

        self.label_app_respository = QLabel(self.frame_app_details)
        self.label_app_respository.setObjectName("label_app_respository")
        self.label_app_respository.setText("<html><head/><body><p><a href=\"https://github.com/czarchmA8/DesktopPet_v3\"><span style=\" text-decoration: underline; color:#9cebff;\">github.com/czarchmA8/DesktopPet_v3</span></a></p></body></html>")
        self.label_app_respository.setOpenExternalLinks(True)

        self.formLayout_app_details.setWidget(1, QFormLayout.ItemRole.FieldRole, self.label_app_respository)


        self.verticalLayout_22.addWidget(self.frame_app_details)

        self.frame_updates = QFrame(self.scrollAreaWidgetContents_2)
        self.frame_updates.setObjectName("frame_updates")
        sizePolicy1.setHeightForWidth(self.frame_updates.sizePolicy().hasHeightForWidth())
        self.frame_updates.setSizePolicy(sizePolicy1)
        self.frame_updates.setStyleSheet("QFrame#frame_updates {\n  background-color: rgba(127, 127, 127, 20);\n  border: 1px solid rgba(127, 127, 127, 60);\n  border-radius: 6px;\n}")
        self.frame_updates.setFrameShape(QFrame.Shape.StyledPanel)
        self.horizontalLayout_info_updates = QHBoxLayout(self.frame_updates)
        self.horizontalLayout_info_updates.setObjectName("horizontalLayout_info_updates")
        self.horizontalLayout_info_updates.setContentsMargins(10, 8, 10, 8)
        self.label_check_for_updates = QLabel(self.frame_updates)
        self.label_check_for_updates.setObjectName("label_check_for_updates")
        sizePolicy5 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        sizePolicy5.setHorizontalStretch(0)
        sizePolicy5.setVerticalStretch(0)
        sizePolicy5.setHeightForWidth(self.label_check_for_updates.sizePolicy().hasHeightForWidth())
        self.label_check_for_updates.setSizePolicy(sizePolicy5)
        self.label_check_for_updates.setStyleSheet("color: #aaa; font-style: italic; font-family: monospace;")
        self.label_check_for_updates.setWordWrap(True)

        self.horizontalLayout_info_updates.addWidget(self.label_check_for_updates)

        self.horizontalSpacer_info_updates = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_info_updates.addItem(self.horizontalSpacer_info_updates)

        self.pushButton_update_application = QPushButton(self.frame_updates)
        self.pushButton_update_application.setObjectName("pushButton_update_application")
        self.pushButton_update_application.setEnabled(False)
        sizePolicy2.setHeightForWidth(self.pushButton_update_application.sizePolicy().hasHeightForWidth())
        self.pushButton_update_application.setSizePolicy(sizePolicy2)

        self.horizontalLayout_info_updates.addWidget(self.pushButton_update_application)

        self.pushButton_check_for_updates = QPushButton(self.frame_updates)
        self.pushButton_check_for_updates.setObjectName("pushButton_check_for_updates")
        sizePolicy2.setHeightForWidth(self.pushButton_check_for_updates.sizePolicy().hasHeightForWidth())
        self.pushButton_check_for_updates.setSizePolicy(sizePolicy2)

        self.horizontalLayout_info_updates.addWidget(self.pushButton_check_for_updates)


        self.verticalLayout_22.addWidget(self.frame_updates)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_22.addItem(self.verticalSpacer_2)

        self.scrollArea_2.setWidget(self.scrollAreaWidgetContents_2)

        self.verticalLayout_19.addWidget(self.scrollArea_2)

        self.tabWidget.addTab(self.tab_info, "")

        self.verticalLayout.addWidget(self.tabWidget)

        self.label_version = QLabel(self.centralwidget)
        self.label_version.setObjectName("label_version")
        self.label_version.setStyleSheet("color: rgba(255, 255, 255, 0.4); font-size: 11px; background: transparent; padding-top: 5px;")
        self.label_version.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout.addWidget(self.label_version)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 33))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        # self.retranslate_ui(MainWindow)

        self.tabWidget.setCurrentIndex(4)


        QMetaObject.connectSlotsByName(MainWindow)

    def retranslate_static_ui(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", "DesktopPet_v3", None))
        self.groupBox_language.setTitle(QCoreApplication.translate("MainWindow", "Language", None))
        self.groupBox_sound.setTitle(QCoreApplication.translate("MainWindow", "Sound", None))
        self.label_volume.setText(QCoreApplication.translate("MainWindow", "Volume:", None))
        self.groupBox_app.setTitle(QCoreApplication.translate("MainWindow", "App", None))
        self.label_show_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Show application", None))
        self.label_show_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_show_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_show_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_show_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_hide_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Hide application", None))
        self.label_hide_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_hide_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_hide_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_hide_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_close_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Close application", None))
        self.label_close_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_close_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_close_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_close_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.groupBox_entities.setTitle(QCoreApplication.translate("MainWindow", "Entities", None))
        self.label_kill_all_entities_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Kill all entities", None))
        self.label_kill_all_entities_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_kill_all_entities_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_kill_all_entities_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_kill_all_entities_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_show_all_entities_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Show all entities", None))
        self.label_show_all_entities_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_show_all_entities_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_show_all_entities_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_show_all_entities_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_hide_all_entities_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Hide all entities", None))
        self.label_hide_all_entities_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_hide_all_entities_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_hide_all_entities_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_hide_all_entities_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_kill_selected_entity_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Kill selected", None))
        self.label_kill_selected_entity_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_kill_selected_entity_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_kill_selected_entity_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_kill_selected_entity_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_show_selected_entity_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Show selected", None))
        self.label_show_selected_entity_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_show_selected_entity_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_show_selected_entity_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_show_selected_entity_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_hide_selected_entity_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Hide selected", None))
        self.label_hide_selected_entity_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_hide_selected_entity_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_hide_selected_entity_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_hide_selected_entity_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))
        self.label_teleport_selected_entity_shortcut_title.setText(QCoreApplication.translate("MainWindow", "Teleport selected", None))
        self.label_teleport_selected_entity_shortcut_value.setText(QCoreApplication.translate("MainWindow", "No keyboard shortcut", None))
        self.pushButton_teleport_selected_entity_shortcut_set.setText(QCoreApplication.translate("MainWindow", "➕ Set", None))

        self.pushButton_teleport_selected_entity_shortcut_remove.setToolTip(QCoreApplication.translate("MainWindow", "Remove shortcut", None))

        self.pushButton_teleport_selected_entity_shortcut_remove.setText(QCoreApplication.translate("MainWindow", "🗑️ Remove", None))

        self.pushButton_open_objects_editor.setToolTip(QCoreApplication.translate("MainWindow", "Opens the built-in hitbox editor for objects", None))

        self.pushButton_open_objects_editor.setText(QCoreApplication.translate("MainWindow", "Open Objects Editor", None))
        self.groupBox_system.setTitle(QCoreApplication.translate("MainWindow", "System", None))

        self.checkBox_check_for_updates.setToolTip(QCoreApplication.translate("MainWindow", "This option does not update the software itself.", None))

        self.checkBox_check_for_updates.setText(QCoreApplication.translate("MainWindow", "Check for updates", None))
        self.checkBox_autostart.setText(QCoreApplication.translate("MainWindow", "Run at system startup", None))
        self.groupBox_advanced.setTitle(QCoreApplication.translate("MainWindow", "Advanced", None))
        self.checkBox_debug_mode.setText(QCoreApplication.translate("MainWindow", "Debug mode", None))
        self.checkBox_hitboxes_overlay.setText(QCoreApplication.translate("MainWindow", "Displaying hitboxes", None))
        self.checkBox_debug_information_window.setText(QCoreApplication.translate("MainWindow", "Information window", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_settings), QCoreApplication.translate("MainWindow", "Settings", None))
        self.groupBox_mods_list.setTitle(QCoreApplication.translate("MainWindow", "Mods (%1)", None))
        self.groupBox_mod_details.setTitle(QCoreApplication.translate("MainWindow", "Mod details", None))
        self.label_mod_preview.setText("")

        self.pushButton_mod_settings.setToolTip(QCoreApplication.translate("MainWindow", "Mod settings", None))

        self.label_mod_author_title.setText(QCoreApplication.translate("MainWindow", "Author:", None))
        self.label_mod_version_title.setText(QCoreApplication.translate("MainWindow", "Version:", None))
        self.label_mod_id_title.setText(QCoreApplication.translate("MainWindow", "ID:", None))
        self.label_mod_description.setText(QCoreApplication.translate("MainWindow", "No description available.", None))
        self.pushButton_load_mod_list.setText(QCoreApplication.translate("MainWindow", "Load mod list", None))
        self.pushButton_save_mod_list.setText(QCoreApplication.translate("MainWindow", "Save Mod List", None))
        self.pushButton_discard_mod_changes.setText(QCoreApplication.translate("MainWindow", "Discard changes", None))
        self.pushButton_save_mod_changes.setText(QCoreApplication.translate("MainWindow", "Save changes", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_mods), QCoreApplication.translate("MainWindow", "Mods", None))
        self.groupBox_entities_list.setTitle(QCoreApplication.translate("MainWindow", "Entities (%1)", None))
        self.lineEdit_entity_search.setPlaceholderText(QCoreApplication.translate("MainWindow", "\U0001f50d Search entities...", None))
        self.groupBox_entity_details.setTitle(QCoreApplication.translate("MainWindow", "Entity details", None))
        self.label_entity_preview.setText("")

        self.pushButton_entity_settings.setToolTip(QCoreApplication.translate("MainWindow", "Mod settings", None))

        self.label_entity_mod_name_title.setText(QCoreApplication.translate("MainWindow", "Mod name:", None))
        self.label_entity_mod_id_title.setText(QCoreApplication.translate("MainWindow", "Mod ID:", None))
        self.label_entity_id_title.setText(QCoreApplication.translate("MainWindow", "ID:", None))
        self.label_entity_description.setText(QCoreApplication.translate("MainWindow", "No description available.", None))
        self.label_entity_position_title.setText(QCoreApplication.translate("MainWindow", "Position:", None))
        self.label_entity_rotation_title.setText(QCoreApplication.translate("MainWindow", "Rotation:", None))
        self.label_entity_velocity_title.setText(QCoreApplication.translate("MainWindow", "Velocity:", None))
        self.label_entity_hwnd_title.setText(QCoreApplication.translate("MainWindow", "HWND:", None))
        self.label_entity_hwnd.setText(QCoreApplication.translate("MainWindow", "unknown", None))
        self.pushButton_kill_all_entities.setText(QCoreApplication.translate("MainWindow", "Kill all entities", None))
        self.pushButton_show_all_entities.setText(QCoreApplication.translate("MainWindow", "Show all entities", None))
        self.pushButton_hide_all_entities.setText(QCoreApplication.translate("MainWindow", "Hide all entities", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_list), QCoreApplication.translate("MainWindow", "List", None))
        ___qtreewidgetitem = self.treeWidget_add_categories.headerItem()
        ___qtreewidgetitem.setText(0, QCoreApplication.translate("MainWindow", "Category", None))

        __sortingEnabled = self.treeWidget_add_categories.isSortingEnabled()
        self.treeWidget_add_categories.setSortingEnabled(False)
        ___qtreewidgetitem1 = self.treeWidget_add_categories.topLevelItem(0)
        ___qtreewidgetitem1.setText(0, QCoreApplication.translate("MainWindow", "All entities", None))
        ___qtreewidgetitem2 = self.treeWidget_add_categories.topLevelItem(1)
        ___qtreewidgetitem2.setText(0, QCoreApplication.translate("MainWindow", "Pets", None))
        ___qtreewidgetitem3 = self.treeWidget_add_categories.topLevelItem(2)
        ___qtreewidgetitem3.setText(0, QCoreApplication.translate("MainWindow", "Objects", None))
        self.treeWidget_add_categories.setSortingEnabled(__sortingEnabled)

        self.groupBox_add_entities.setTitle(QCoreApplication.translate("MainWindow", "Entities (%1)", None))
        self.lineEdit_add_search.setPlaceholderText(QCoreApplication.translate("MainWindow", "🔍 Search entities...", None))
        self.groupBox_add_entity_details.setTitle(QCoreApplication.translate("MainWindow", "Entity details", None))
        self.label_add_entity_preview.setText("")

        self.pushButton_add_entity_settings.setToolTip(QCoreApplication.translate("MainWindow", "Mod settings", None))

        self.label_add_entity_mod_name_title.setText(QCoreApplication.translate("MainWindow", "Mod name:", None))
        self.label_add_entity_mod_id_title.setText(QCoreApplication.translate("MainWindow", "Mod ID:", None))
        self.label_add_entity_id_title.setText(QCoreApplication.translate("MainWindow", "ID:", None))
        self.pushButton_add_entity.setText(QCoreApplication.translate("MainWindow", "➕ Add to list", None))
        self.label_add_entity_description.setText(QCoreApplication.translate("MainWindow", "No description available.", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_add), QCoreApplication.translate("MainWindow", "Add", None))
        self.label_app_banner.setText("")
        self.label_app_version.setText(QCoreApplication.translate("MainWindow", "version: %1  •  %2", None))
        self.label_app_description.setText(QCoreApplication.translate("MainWindow", "An interactive desktop pet application featuring physics simulation, a control panel, and sophisticated system window behavior. The application is open-source and anyone can support its development.", None))
        self.label_app_author_title.setText(QCoreApplication.translate("MainWindow", "Author:", None))
        self.label_app_repository_title.setText(QCoreApplication.translate("MainWindow", "Repository:", None))
        self.label_check_for_updates.setText(QCoreApplication.translate("MainWindow", "The version has not been checked yet", None))
        self.pushButton_update_application.setText(QCoreApplication.translate("MainWindow", "Update", None))
        self.pushButton_check_for_updates.setText(QCoreApplication.translate("MainWindow", "🔄 Check for updates", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_info), QCoreApplication.translate("MainWindow", "Info", None))
        self.label_version.setText(QCoreApplication.translate("MainWindow", "Version: %1", None))
