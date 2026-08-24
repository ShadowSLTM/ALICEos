"""
Application Paramètres d'ALICEos.
Permet de changer le thème clair/sombre, le fond d'écran, le nom d'utilisateur,
le volume système, et le mot de passe de session.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QSlider, QTabWidget, QColorDialog, QStackedWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from ui.desktop import GRADIENTS, DEFAULT_CUSTOM_COLORS

WALLPAPER_LABELS = {
    "gradient_purple": "Violet",
    "gradient_blue": "Bleu",
    "gradient_sunset": "Coucher de soleil",
    "gradient_forest": "Forêt",
    "gradient_ocean": "Océan",
    "gradient_fire": "Feu",
    "gradient_mint": "Menthe",
    "gradient_rose": "Rose",
    "gradient_midnight": "Minuit",
    "gradient_gold": "Or",
    "solid_dark": "Sombre uni",
    "solid_light": "Clair uni",
}


class ColorSwatch(QPushButton):
    """Bouton carré affichant une couleur, cliquable pour l'éditer via un sélecteur système."""

    color_changed = Signal(str)

    def __init__(self, initial_hex):
        super().__init__()
        self.setFixedSize(48, 32)
        self.hex_color = initial_hex
        self._refresh()
        self.clicked.connect(self._pick_color)

    def _refresh(self):
        self.setStyleSheet(
            f"background-color: {self.hex_color}; border: 2px solid rgba(255,255,255,60); border-radius: 6px;"
        )

    def _pick_color(self):
        chosen = QColorDialog.getColor(QColor(self.hex_color), self, "Choisir une couleur")
        if chosen.isValid():
            self.hex_color = chosen.name()
            self._refresh()
            self.color_changed.emit(self.hex_color)


class SettingsApp(QWidget):
    theme_changed = Signal(str)
    wallpaper_changed = Signal(str)

    def __init__(self, settings, notifier=None):
        super().__init__()
        self.settings = settings
        self.notifier = notifier

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)

        tabs.addTab(self._build_appearance_tab(), "Apparence")
        tabs.addTab(self._build_account_tab(), "Compte")
        tabs.addTab(self._build_system_tab(), "Système")

    # --- Onglet Apparence ---

    def _build_appearance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Thème"))
        theme_row = QHBoxLayout()
        light_btn = QPushButton("Clair")
        dark_btn = QPushButton("Sombre")
        light_btn.clicked.connect(lambda: self._set_theme("light"))
        dark_btn.clicked.connect(lambda: self._set_theme("dark"))
        theme_row.addWidget(light_btn)
        theme_row.addWidget(dark_btn)
        layout.addLayout(theme_row)

        layout.addWidget(QLabel("Fond d'écran"))
        self.wallpaper_combo = QComboBox()
        for key, label in WALLPAPER_LABELS.items():
            self.wallpaper_combo.addItem(label, key)
        self.wallpaper_combo.addItem("Personnalisé...", "custom")

        current = self.settings.get("wallpaper", "gradient_purple")
        index = self.wallpaper_combo.findData(current)
        self.wallpaper_combo.setCurrentIndex(index if index >= 0 else 0)
        self.wallpaper_combo.currentIndexChanged.connect(self._on_wallpaper_selected)
        layout.addWidget(self.wallpaper_combo)

        # Bloc de personnalisation, visible uniquement quand "Personnalisé..." est choisi
        self.custom_block = QWidget()
        custom_layout = QVBoxLayout(self.custom_block)
        custom_layout.setContentsMargins(0, 8, 0, 0)
        custom_layout.addWidget(QLabel("Couleurs du dégradé (haut, milieu, bas)"))

        swatch_row = QHBoxLayout()
        saved_colors = self.settings.get("custom_wallpaper_colors", DEFAULT_CUSTOM_COLORS)
        self.swatches = []
        for i in range(3):
            color = saved_colors[i] if i < len(saved_colors) else DEFAULT_CUSTOM_COLORS[i]
            swatch = ColorSwatch(color)
            swatch.color_changed.connect(self._on_custom_color_changed)
            swatch_row.addWidget(swatch)
            self.swatches.append(swatch)
        swatch_row.addStretch()
        custom_layout.addLayout(swatch_row)

        apply_btn = QPushButton("Appliquer les couleurs personnalisées")
        apply_btn.clicked.connect(self._apply_custom_wallpaper)
        custom_layout.addWidget(apply_btn)

        layout.addWidget(self.custom_block)
        self.custom_block.setVisible(current == "custom")

        layout.addStretch()
        return tab

    def _set_theme(self, theme):
        self.settings.set("theme", theme)
        self.theme_changed.emit(theme)
        if self.notifier:
            self.notifier.notify("Thème appliqué", f"Le thème {theme} a été activé.")

    def _on_wallpaper_selected(self, index):
        key = self.wallpaper_combo.itemData(index)
        self.custom_block.setVisible(key == "custom")
        if key == "custom":
            self._apply_custom_wallpaper()
        else:
            self._set_wallpaper(key)

    def _set_wallpaper(self, name):
        self.settings.set("wallpaper", name)
        self.wallpaper_changed.emit(name)

    def _on_custom_color_changed(self, _hex_color):
        # Applique immédiatement pour un retour visuel en direct pendant le choix des couleurs
        self._apply_custom_wallpaper()

    def _apply_custom_wallpaper(self):
        colors = [s.hex_color for s in self.swatches]
        self.settings.set("custom_wallpaper_colors", colors)
        self._set_wallpaper("custom")

    # --- Onglet Compte ---

    def _build_account_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Nom d'utilisateur"))
        self.username_field = QLineEdit(self.settings.get("username", "Utilisateur"))
        layout.addWidget(self.username_field)
        save_name_btn = QPushButton("Enregistrer le nom")
        save_name_btn.clicked.connect(self._save_username)
        layout.addWidget(save_name_btn)

        layout.addWidget(QLabel("Nouveau mot de passe"))
        self.password_field = QLineEdit()
        self.password_field.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_field)
        save_pwd_btn = QPushButton("Changer le mot de passe")
        save_pwd_btn.clicked.connect(self._save_password)
        layout.addWidget(save_pwd_btn)

        layout.addStretch()
        return tab

    def _save_username(self):
        name = self.username_field.text().strip()
        if name:
            self.settings.set("username", name)
            if self.notifier:
                self.notifier.notify("Profil mis à jour", "Le nom d'utilisateur a été changé.")

    def _save_password(self):
        pwd = self.password_field.text()
        if pwd:
            self.settings.set_password(pwd)
            self.password_field.clear()
            if self.notifier:
                self.notifier.notify("Sécurité", "Le mot de passe a été mis à jour.")

    # --- Onglet Système ---

    def _build_system_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("Volume"))
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(self.settings.get("volume", 70))
        self.volume_slider.valueChanged.connect(lambda v: self.settings.set("volume", v))
        layout.addWidget(self.volume_slider)

        about = QLabel("ALICEos 1.0\nSystème d'exploitation virtuel construit avec Python et PySide6.")
        about.setStyleSheet("color: #9a9ab0; margin-top: 20px;")
        layout.addWidget(about)

        layout.addStretch()
        return tab