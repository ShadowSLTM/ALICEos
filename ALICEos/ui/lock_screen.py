"""
Écran de connexion et écran de verrouillage d'ALICEos.
Les deux partagent la même logique de vérification du mot de passe auprès du SettingsManager,
mais l'écran de verrouillage conserve le bureau existant en arrière-plan (session non fermée).
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QGraphicsOpacityEffect,
    QApplication,
)
from PySide6.QtCore import Qt, Signal, QDateTime, QTimer
from PySide6.QtGui import QFont


class LockScreen(QWidget):
    """Écran modal affichant l'heure, un champ mot de passe, et un bouton de déverrouillage."""

    unlocked = Signal()

    def __init__(self, settings, mode="login"):
        """mode: 'login' (première connexion) ou 'lock' (verrouillage de session)."""
        super().__init__()
        self.settings = settings
        self.mode = mode

        self.setStyleSheet("background-color: rgba(20, 20, 28, 235);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(18)

        # Horloge
        self.clock = QLabel()
        self.clock.setAlignment(Qt.AlignCenter)
        self.clock.setStyleSheet("color: white; background: transparent;")
        self.clock.setFont(QFont("Segoe UI", 44, QFont.Light))
        layout.addWidget(self.clock)

        # Date
        self.date_label = QLabel()
        self.date_label.setAlignment(Qt.AlignCenter)
        self.date_label.setStyleSheet(
            "color: #c4c4d6; background: transparent; font-size: 14px;"
        )
        layout.addWidget(self.date_label)

        layout.addSpacing(20)

        # Avatar
        avatar = QLabel(self.settings.get("username", "Utilisateur")[0].upper())
        avatar.setFixedSize(74, 74)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            background-color: #8b5cf6;
            color: white;
            border-radius: 37px;
            font-size: 28px;
            font-weight: 600;
        """)
        layout.addWidget(avatar, alignment=Qt.AlignCenter)

        # Nom d'utilisateur
        username = QLabel(self.settings.get("username", "Utilisateur"))
        username.setAlignment(Qt.AlignCenter)
        username.setStyleSheet("""
            color: white;
            background: transparent;
            font-size: 16px;
            font-weight: 500;
        """)
        layout.addWidget(username)

        # Champ mot de passe
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Mot de passe")
        self.password_field.setEchoMode(QLineEdit.Password)
        self.password_field.setFixedWidth(240)
        self.password_field.setStyleSheet("""
            QLineEdit {
                background-color: rgba(255,255,255,20);
                color: white;
                border: 1px solid #55556a;
                border-radius: 18px;
                padding: 10px 16px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #a478f7;
            }
        """)
        self.password_field.returnPressed.connect(self._try_unlock)
        layout.addWidget(self.password_field, alignment=Qt.AlignCenter)

        # Indice
        self.hint = QLabel("Indice : le mot de passe par défaut est « alice »")
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setStyleSheet("""
            color: #7c7c94;
            background: transparent;
            font-size: 11px;
        """)
        layout.addWidget(self.hint)

        # Message d'erreur
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("""
            color: #f76d6d;
            background: transparent;
            font-size: 12px;
        """)
        layout.addWidget(self.error_label)

        # Bouton principal
        unlock_btn = QPushButton(
            "Se connecter" if mode == "login" else "Déverrouiller"
        )
        unlock_btn.setFixedWidth(240)
        unlock_btn.setStyleSheet("""
            QPushButton {
                background-color: #8b5cf6;
                color: white;
                border: none;
                border-radius: 18px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #a478f7;
            }
        """)
        unlock_btn.clicked.connect(self._try_unlock)
        layout.addWidget(unlock_btn, alignment=Qt.AlignCenter)

        # Bouton Quitter
        quit_btn = QPushButton("Quitter")
        quit_btn.setFixedWidth(240)
        quit_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255,255,255,20);
                color: white;
                border: 1px solid #55556a;
                border-radius: 18px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: rgba(255,255,255,35);
            }
        """)
        quit_btn.clicked.connect(QApplication.instance().quit)
        layout.addWidget(quit_btn, alignment=Qt.AlignCenter)

        # Horloge
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        now = QDateTime.currentDateTime()
        self.clock.setText(now.toString("HH:mm"))
        self.date_label.setText(now.toString("dddd d MMMM yyyy"))

    def _try_unlock(self):
        if self.settings.check_password(self.password_field.text()):
            self.error_label.setText("")
            self.password_field.clear()
            self.unlocked.emit()
        else:
            self.error_label.setText("Mot de passe incorrect.")
            self.password_field.clear()

    def showEvent(self, event):
        self.password_field.setFocus()
        super().showEvent(event)