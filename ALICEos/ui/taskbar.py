"""
Barre des tâches d'ALICEos.
Regroupe le bouton Démarrer (avec menu d'applications), la liste des fenêtres ouvertes
(pour les faire passer au premier plan ou les réduire), l'horloge, et une zone système
avec accès rapide aux paramètres et au verrouillage de session.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QMenu, QFrame
from PySide6.QtCore import Qt, QTimer, QDateTime, Signal
from PySide6.QtGui import QAction


APPS = [
    ("file_explorer", "🗂️", "Explorateur de fichiers"),
    ("terminal", "💻", "Terminal"),
    ("calculator", "🧮", "Calculatrice"),
    ("browser", "🌐", "Navigateur"),
    ("notepad", "📝", "Bloc-notes"),
    ("bullet_hell", "🌸", "Bullet Hell"),
    ("settings", "⚙️", "Paramètres"),
    ("task_manager", "📊", "Gestionnaire de tâches"),
]


class Taskbar(QWidget):
    launch_app = Signal(str)
    lock_requested = Signal()

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.setFixedHeight(48)
        self.setStyleSheet("""
            Taskbar { background-color: rgba(20, 20, 30, 200); }
        """)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("Taskbar")
        self.setStyleSheet("""
            #Taskbar { background-color: rgba(18, 18, 26, 215); border-top: 1px solid rgba(255,255,255,20); }
            QPushButton { background: transparent; border: none; border-radius: 6px; padding: 6px 10px; color: white; }
            QPushButton:hover { background-color: rgba(255,255,255,30); }
            QLabel { color: white; background: transparent; }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)

        self.start_btn = QPushButton("✨ ALICEos")
        self.start_btn.setStyleSheet("font-weight: 600;")
        self.start_btn.clicked.connect(self._show_start_menu)
        layout.addWidget(self.start_btn)

        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setStyleSheet("color: rgba(255,255,255,40);")
        layout.addWidget(sep)

        # Zone des fenêtres ouvertes (boutons ajoutés dynamiquement)
        self.window_buttons_layout = QHBoxLayout()
        self.window_buttons_layout.setSpacing(4)
        layout.addLayout(self.window_buttons_layout)
        self._window_buttons = {}

        layout.addStretch()

        self.notif_btn = QPushButton("🔔")
        layout.addWidget(self.notif_btn)

        self.lock_btn = QPushButton("🔒")
        self.lock_btn.clicked.connect(self.lock_requested.emit)
        layout.addWidget(self.lock_btn)

        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("font-weight: 500; padding: 0 8px;")
        layout.addWidget(self.clock_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        now = QDateTime.currentDateTime()
        self.clock_label.setText(now.toString("HH:mm") + "\n" + now.toString("dd/MM/yyyy"))

    def _show_start_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu { padding: 8px; }")
        title = QAction(f"  {self.settings.get('username', 'Utilisateur')}", self)
        title.setEnabled(False)
        menu.addAction(title)
        menu.addSeparator()
        for app_id, icon, label in APPS:
            action = QAction(f"{icon}  {label}", self)
            action.triggered.connect(lambda checked=False, a=app_id: self.launch_app.emit(a))
            menu.addAction(action)
        menu.addSeparator()
        lock_action = QAction("🔒  Verrouiller la session", self)
        lock_action.triggered.connect(self.lock_requested.emit)
        menu.addAction(lock_action)
        menu.exec(self.mapToGlobal(self.start_btn.pos() + self.start_btn.rect().topRight()) - self._menu_offset(menu))

    def _menu_offset(self, menu):
        from PySide6.QtCore import QPoint
        return QPoint(menu.sizeHint().width(), -menu.sizeHint().height() + self.start_btn.height())

    # --- Suivi des fenêtres ouvertes ---

    def register_window(self, sub_window):
        btn = QPushButton(f"{sub_window.icon_text} {sub_window.windowTitle()}")
        btn.setCheckable(True)
        btn.setChecked(True)
        btn.setStyleSheet("padding: 6px 10px;")
        btn.clicked.connect(lambda: self._toggle_window(sub_window))
        self.window_buttons_layout.addWidget(btn)
        self._window_buttons[sub_window] = btn

    def unregister_window(self, sub_window):
        btn = self._window_buttons.pop(sub_window, None)
        if btn:
            btn.deleteLater()

    def _toggle_window(self, sub_window):
        try:
            if sub_window.isMinimized():
                sub_window.showNormal()
                sub_window.mdiArea().setActiveSubWindow(sub_window)
            else:
                sub_window.showMinimized()
        except RuntimeError:
            pass
