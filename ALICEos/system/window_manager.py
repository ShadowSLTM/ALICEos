"""
Gestionnaire de fenêtres pour ALICEos.
S'appuie sur QMdiArea, qui fournit nativement le déplacement, le redimensionnement,
la réduction, l'agrandissement et la fermeture des fenêtres internes. Ce module ajoute
par-dessus des animations d'ouverture/fermeture et un suivi centralisé pour le gestionnaire
de tâches et la barre des tâches.
"""

from PySide6.QtWidgets import QMdiSubWindow, QGraphicsOpacityEffect
from PySide6.QtCore import QPropertyAnimation, Qt, QEasingCurve


class AppWindow(QMdiSubWindow):
    """Sous-fenêtre MDI représentant une application ouverte, avec identité pour le taskbar."""

    def __init__(self, app_id, title, icon_text="🗔"):
        super().__init__()
        self.app_id = app_id
        self.icon_text = icon_text
        self.setWindowTitle(title)
        self.setAttribute(Qt.WA_DeleteOnClose)


class WindowManager:
    """Ouvre, ferme et suit les fenêtres actives d'ALICEos au sein d'un QMdiArea."""

    def __init__(self, mdi_area, taskbar=None):
        self.mdi = mdi_area
        self.taskbar = taskbar
        self.windows = []

    def open_window(self, app_id, title, widget, icon_text="🗔", size=(640, 420)):
        """Crée une sous-fenêtre, y insère le widget applicatif, et l'anime à l'ouverture."""
        existing = self.find_window(app_id)
        if existing and getattr(existing, "single_instance", False):
            self.mdi.setActiveSubWindow(existing)
            return existing

        sub = AppWindow(app_id, title, icon_text)
        sub.setWidget(widget)
        sub.resize(*size)
        self.mdi.addSubWindow(sub)

        # Positionnement en cascade légère pour éviter l'empilement parfait
        offset = 28 * (len(self.windows) % 8)
        sub.move(40 + offset, 30 + offset)

        effect = QGraphicsOpacityEffect(sub)
        sub.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", sub)
        anim.setDuration(220)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        sub._open_anim = anim

        sub.show()
        anim.start()
        self.mdi.setActiveSubWindow(sub)

        self.windows.append(sub)
        sub.destroyed.connect(lambda: self._on_window_closed(sub))
        if self.taskbar:
            self.taskbar.register_window(sub)
        return sub

    def find_window(self, app_id):
        for w in self.windows:
            if w.app_id == app_id:
                return w
        return None

    def close_window(self, sub):
        sub.close()

    def _on_window_closed(self, sub):
        if sub in self.windows:
            self.windows.remove(sub)
        if self.taskbar:
            self.taskbar.unregister_window(sub)
