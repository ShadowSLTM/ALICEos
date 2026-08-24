"""
Bureau d'ALICEos.
Peint le fond d'écran (dégradé selon le choix de l'utilisateur), héberge la zone MDI
qui contient les fenêtres d'applications, et propose un menu contextuel au clic droit.
Cette version ne place aucune icône sur le bureau : l'accès aux applications se fait
uniquement via le menu Démarrer déroulant de la barre des tâches.
"""

from PySide6.QtWidgets import QWidget, QMdiArea, QVBoxLayout, QMenu
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QLinearGradient, QColor, QAction


GRADIENTS = {
    "gradient_purple": [QColor("#3a1c71"), QColor("#8b5cf6"), QColor("#d76d77")],
    "gradient_blue": [QColor("#0f2027"), QColor("#2c5364"), QColor("#4facfe")],
    "gradient_sunset": [QColor("#ff512f"), QColor("#f09819"), QColor("#dd2476")],
    "gradient_forest": [QColor("#134e5e"), QColor("#2e8b57"), QColor("#71b280")],
    "gradient_ocean": [QColor("#1a2980"), QColor("#26d0ce"), QColor("#1a2980")],
    "gradient_fire": [QColor("#8e0e00"), QColor("#e0521a"), QColor("#f7b733")],
    "gradient_mint": [QColor("#0f9b8e"), QColor("#43cea2"), QColor("#a8ff78")],
    "gradient_rose": [QColor("#c9184a"), QColor("#ff4d8d"), QColor("#ffb3c6")],
    "gradient_midnight": [QColor("#0f0c29"), QColor("#302b63"), QColor("#24243e")],
    "gradient_gold": [QColor("#8a6d00"), QColor("#e0b400"), QColor("#fff1a8")],
    "solid_dark": [QColor("#1a1b26"), QColor("#1a1b26"), QColor("#1a1b26")],
    "solid_light": [QColor("#e8eaf2"), QColor("#e8eaf2"), QColor("#e8eaf2")],
}

DEFAULT_CUSTOM_COLORS = ["#3a1c71", "#8b5cf6", "#d76d77"]


class Desktop(QWidget):
    """Widget racine du bureau : fond d'écran et zone MDI pour les fenêtres."""

    context_action = Signal(str)

    def __init__(self, settings):
        super().__init__()
        self.settings = settings
        self.wallpaper_name = settings.get("wallpaper", "gradient_purple")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.mdi = QMdiArea()
        self.mdi.setAttribute(Qt.WA_TranslucentBackground)
        self.mdi.setFrameShape(QMdiArea.NoFrame)
        self.mdi.setBackground(Qt.transparent)
        self.mdi.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.mdi.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.mdi)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def set_wallpaper(self, name):
        self.wallpaper_name = name
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        colors = self._current_colors()
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        if len(colors) == 1:
            painter.fillRect(self.rect(), colors[0])
            return
        step = 1.0 / (len(colors) - 1)
        for i, color in enumerate(colors):
            gradient.setColorAt(min(i * step, 1.0), color)
        painter.fillRect(self.rect(), gradient)

    def _current_colors(self):
        """Retourne la liste de QColor à utiliser pour le fond, préréglé ou personnalisé."""
        if self.wallpaper_name == "custom":
            hex_colors = self.settings.get("custom_wallpaper_colors", DEFAULT_CUSTOM_COLORS)
            colors = [QColor(h) for h in hex_colors if QColor(h).isValid()]
            return colors if colors else [QColor(c) for c in DEFAULT_CUSTOM_COLORS]
        return GRADIENTS.get(self.wallpaper_name, GRADIENTS["gradient_purple"])

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        new_folder = QAction("Nouveau dossier", self)
        new_folder.triggered.connect(lambda: self.context_action.emit("new_folder"))
        menu.addAction(new_folder)

        refresh = QAction("Actualiser", self)
        refresh.triggered.connect(lambda: self.context_action.emit("refresh"))
        menu.addAction(refresh)

        menu.addSeparator()

        change_wallpaper = QAction("Changer le fond d'écran", self)
        change_wallpaper.triggered.connect(lambda: self.context_action.emit("open_settings"))
        menu.addAction(change_wallpaper)

        open_terminal = QAction("Ouvrir un terminal ici", self)
        open_terminal.triggered.connect(lambda: self.context_action.emit("open_terminal"))
        menu.addAction(open_terminal)

        menu.exec(self.mapToGlobal(pos))