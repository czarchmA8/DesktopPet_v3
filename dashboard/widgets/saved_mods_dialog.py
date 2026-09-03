from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton, QMessageBox

class SavedModsListDialog(QDialog):
    """Dialogue for selecting a saved list of mods to load or remove."""

    def __init__(self, saved_lists: dict[str, list[str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle(QCoreApplication.translate("SavedModsListDialog", "Load mod list", None))
        self.saved_lists = saved_lists
        self.selected_name: str | None = None
        self.modified = False

        layout = QVBoxLayout(self)

        self.list_widget = QListWidget(self)
        for name in sorted(self.saved_lists.keys(), key=str.lower):
            self.list_widget.addItem(name)
        self.list_widget.currentRowChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(lambda _: self._accept_load())
        layout.addWidget(self.list_widget)

        button_layout = QHBoxLayout()
        self.button_load = QPushButton(QCoreApplication.translate("SavedModsListDialog", "Load", None), self)
        self.button_delete = QPushButton(QCoreApplication.translate("SavedModsListDialog", "Delete", None), self)
        self.button_cancel = QPushButton(QCoreApplication.translate("SavedModsListDialog", "Cancel", None), self)
        button_layout.addWidget(self.button_load)
        button_layout.addWidget(self.button_delete)
        button_layout.addWidget(self.button_cancel)
        layout.addLayout(button_layout)

        self.button_load.clicked.connect(self._accept_load)
        self.button_delete.clicked.connect(self._on_delete)
        self.button_cancel.clicked.connect(self.reject)

        self.button_load.setEnabled(False)
        self.button_delete.setEnabled(False)
        if self.list_widget.count():
            self.list_widget.setCurrentRow(0)

    def _on_selection_changed(self, row: int) -> None:
        has_selection = row >= 0
        self.button_load.setEnabled(has_selection)
        self.button_delete.setEnabled(has_selection)

    def _accept_load(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        self.selected_name = item.text()
        self.accept()

    def _on_delete(self) -> None:
        item = self.list_widget.currentItem()
        if item is None:
            return
        name = item.text()
        confirm = QMessageBox.question(
            self,
            QCoreApplication.translate("SavedModsListDialog", "Delete mod list", None),
            QCoreApplication.translate("SavedModsListDialog", "Delete saved list \"%1\"?", None).replace("%1", name),
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        del self.saved_lists[name]
        self.modified = True
        self.list_widget.takeItem(self.list_widget.row(item))
