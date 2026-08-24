"""
Calculatrice d'ALICEos. Interface simple en grille, évaluation sécurisée des expressions
(uniquement chiffres et opérateurs arithmétiques de base, aucun eval() sur du texte libre).
"""

import re
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QLineEdit, QPushButton
from PySide6.QtCore import Qt


BUTTONS = [
    ["C", "⌫", "%", "÷"],
    ["7", "8", "9", "×"],
    ["4", "5", "6", "−"],
    ["1", "2", "3", "+"],
    ["±", "0", ".", "="],
]

SAFE_EXPR = re.compile(r"^[0-9+\-*/.%() ]+$")


class Calculator(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.display = QLineEdit("0")
        self.display.setAlignment(Qt.AlignRight)
        self.display.setReadOnly(True)
        self.display.setStyleSheet("font-size: 28px; padding: 14px;")
        layout.addWidget(self.display)

        grid = QGridLayout()
        for row, row_keys in enumerate(BUTTONS):
            for col, key in enumerate(row_keys):
                btn = QPushButton(key)
                btn.setFixedHeight(52)
                btn.setStyleSheet("font-size: 16px;")
                btn.clicked.connect(lambda checked=False, k=key: self._on_key(k))
                grid.addWidget(btn, row, col)
        layout.addLayout(grid)

        self.expression = ""

    def _on_key(self, key):
        if key == "C":
            self.expression = ""
        elif key == "⌫":
            self.expression = self.expression[:-1]
        elif key == "=":
            self._evaluate()
            return
        elif key == "±":
            if self.expression.startswith("-"):
                self.expression = self.expression[1:]
            else:
                self.expression = "-" + self.expression
        else:
            mapping = {"÷": "/", "×": "*", "−": "-", "%": "%"}
            self.expression += mapping.get(key, key)
        self.display.setText(self.expression if self.expression else "0")

    def _evaluate(self):
        expr = self.expression.replace("%", "/100")
        if not expr or not SAFE_EXPR.match(self.expression):
            self.display.setText("Erreur")
            self.expression = ""
            return
        try:
            result = eval(expr, {"__builtins__": {}}, {})
            self.display.setText(str(result))
            self.expression = str(result)
        except (ZeroDivisionError, SyntaxError, ValueError):
            self.display.setText("Erreur")
            self.expression = ""
