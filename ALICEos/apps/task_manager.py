"""
Gestionnaire de tâches d'ALICEos.
Liste les fenêtres actuellement ouvertes dans le gestionnaire de fenêtres,
avec la possibilité de forcer leur fermeture.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QPushButton, QLabel
from PySide6.QtCore import Qt, QTimer


class TaskManager(QWidget):
    def __init__(self, window_manager):
        super().__init__()
        self.wm = window_manager

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Applications en cours d'exécution"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        btn_row = QHBoxLayout()
        end_btn = QPushButton("Terminer la tâche")
        end_btn.clicked.connect(self._end_task)
        btn_row.addWidget(end_btn)
        layout.addLayout(btn_row)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(1000)
        self._refresh()

    def _refresh(self):
        self.list_widget.clear()
        for w in self.wm.windows:
            item = QListWidgetItem(f"{w.icon_text}  {w.windowTitle()}")
            item.setData(Qt.UserRole, w)
            self.list_widget.addItem(item)

    def _end_task(self):
        item = self.list_widget.currentItem()
        if item:
            window = item.data(Qt.UserRole)
            if window:
                window.close()
            self._refresh()
