"""
Écran de démarrage d'ALICEos.
Affiche le logo, une barre de progression et un texte d'état qui évolue,
avant de déclencher automatiquement l'ouverture de l'écran de connexion.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QProgressBar, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal
from PySide6.QtGui import QFont


BOOT_STEPS = [
    "Initialisation du noyau ALICEos...",
    "Chargement des pilotes virtuels...",
    "Montage du système de fichiers...",
    "Démarrage des services système...",
    "Préparation de l'interface graphique...",
    "Bienvenue.",
]


class BootScreen(QWidget):
    """Écran plein cadre affiché au lancement de l'application, avant la connexion."""

    finished = Signal()

    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: #14141c;")
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(24)

        self.logo = QLabel("ALICEos")
        self.logo.setAlignment(Qt.AlignCenter)
        font = QFont("Segoe UI", 46, QFont.Bold)
        self.logo.setFont(font)
        self.logo.setStyleSheet("color: #a478f7; background: transparent;")
        layout.addWidget(self.logo)

        self.subtitle = QLabel("système d'exploitation virtuel")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("color: #7c7c94; background: transparent; font-size: 13px; letter-spacing: 2px;")
        layout.addWidget(self.subtitle)

        self.progress = QProgressBar()
        self.progress.setFixedWidth(360)
        self.progress.setRange(0, len(BOOT_STEPS))
        self.progress.setTextVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { background-color: #22222e; border-radius: 4px; height: 8px; }
            QProgressBar::chunk { background-color: #a478f7; border-radius: 4px; }
        """)
        layout.addWidget(self.progress, alignment=Qt.AlignCenter)

        self.status = QLabel(BOOT_STEPS[0])
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("color: #9a9ab0; background: transparent; font-size: 12px;")
        layout.addWidget(self.status)

        # Fondu d'entrée du logo pour une ouverture plus douce
        effect = QGraphicsOpacityEffect(self.logo)
        self.logo.setGraphicsEffect(effect)
        self.anim = QPropertyAnimation(effect, b"opacity")
        self.anim.setDuration(900)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()

        self.step_index = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._next_step)
        self.timer.start(450)

    def _next_step(self):
        self.step_index += 1
        self.progress.setValue(self.step_index)
        if self.step_index < len(BOOT_STEPS):
            self.status.setText(BOOT_STEPS[self.step_index])
        if self.step_index >= len(BOOT_STEPS):
            self.timer.stop()
            QTimer.singleShot(400, self.finished.emit)
