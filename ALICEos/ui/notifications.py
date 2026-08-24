"""
Système de notifications toast pour ALICEos.
Chaque notification apparaît en bas à droite du bureau, reste visible quelques secondes,
puis disparaît avec un fondu. Le NotificationCenter gère l'empilement de plusieurs toasts.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QPoint


class Toast(QWidget):
    """Une notification individuelle, avec titre et message."""

    def __init__(self, parent, title, message, accent):
        super().__init__(parent)
        self.setFixedWidth(300)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget {{ background-color: #2f3142; border-radius: 10px; border-left: 4px solid {accent}; }}
            QLabel {{ background: transparent; }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        title_label = QLabel(title)
        title_label.setStyleSheet("color: white; font-weight: 600; font-size: 13px;")
        layout.addWidget(title_label)
        msg_label = QLabel(message)
        msg_label.setStyleSheet("color: #c4c4d6; font-size: 12px;")
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)

        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0)


class NotificationCenter:
    """Gère l'affichage empilé des notifications au-dessus du bureau."""

    def __init__(self, desktop_widget):
        self.desktop = desktop_widget
        self.active_toasts = []

    def notify(self, title, message, accent="#8b5cf6", duration=3500):
        toast = Toast(self.desktop, title, message, accent)
        toast.adjustSize()
        self._reposition_and_show(toast)
        QTimer.singleShot(duration, lambda: self._dismiss(toast))

    def _reposition_and_show(self, toast):
        margin = 16
        x = self.desktop.width() - toast.width() - margin
        y = self.desktop.height() - margin
        for existing in self.active_toasts:
            y -= existing.height() + 10
        y -= toast.height()
        toast.move(x, y + 20)
        toast.show()
        toast.raise_()
        self.active_toasts.append(toast)

        anim_fade = QPropertyAnimation(toast.effect, b"opacity", toast)
        anim_fade.setDuration(250)
        anim_fade.setStartValue(0)
        anim_fade.setEndValue(1)
        anim_fade.start()
        toast._anim_fade = anim_fade

        anim_move = QPropertyAnimation(toast, b"pos", toast)
        anim_move.setDuration(250)
        anim_move.setStartValue(toast.pos())
        anim_move.setEndValue(QPoint(toast.x(), toast.y() - 20))
        anim_move.start()
        toast._anim_move = anim_move

    def _dismiss(self, toast):
        if toast not in self.active_toasts:
            return
        anim = QPropertyAnimation(toast.effect, b"opacity", toast)
        anim.setDuration(300)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.finished.connect(lambda: self._cleanup(toast))
        anim.start()
        toast._anim_out = anim

    def _cleanup(self, toast):
        if toast in self.active_toasts:
            self.active_toasts.remove(toast)
        toast.deleteLater()
