"""
Définit les palettes et feuilles de style (QSS) pour les thèmes clair et sombre d'ALICEos.
Centraliser les thèmes ici permet à n'importe quelle fenêtre de l'OS de s'adapter
instantanément lorsque l'utilisateur change de thème dans les paramètres.
"""

DARK = {
    "bg": "#1e1f29",
    "bg_alt": "#282a3a",
    "surface": "#2f3142",
    "surface_hover": "#3a3d52",
    "accent": "#8b5cf6",
    "accent_hover": "#a478f7",
    "text": "#f2f2f7",
    "text_dim": "#9a9ab0",
    "border": "#3f4156",
    "danger": "#f76d6d",
    "success": "#5ce0a0",
}

LIGHT = {
    "bg": "#eef0f6",
    "bg_alt": "#ffffff",
    "surface": "#ffffff",
    "surface_hover": "#e7e9f5",
    "accent": "#7c3aed",
    "accent_hover": "#6d28d9",
    "text": "#1c1d29",
    "text_dim": "#6b6d80",
    "border": "#d8dae6",
    "danger": "#e5484d",
    "success": "#2fa572",
}


def palette(theme_name):
    return DARK if theme_name == "dark" else LIGHT


def build_qss(theme_name):
    p = palette(theme_name)
    return f"""
    QWidget {{
        background-color: {p['bg']};
        color: {p['text']};
        font-family: 'Segoe UI', 'Ubuntu', sans-serif;
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background-color: {p['bg']};
    }}
    QPushButton {{
        background-color: {p['surface']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{
        background-color: {p['surface_hover']};
        border: 1px solid {p['accent']};
    }}
    QPushButton:pressed {{
        background-color: {p['accent']};
        color: white;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QTreeWidget {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {p['accent']};
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
    }}
    QScrollBar::handle:vertical {{
        background: {p['border']};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p['accent']};
    }}
    QMenu {{
        background-color: {p['surface']};
        border: 1px solid {p['border']};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 6px 24px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {p['accent']};
        color: white;
    }}
    QLabel#title {{
        font-size: 16px;
        font-weight: 600;
    }}
    QMdiArea {{
        background-color: transparent;
    }}
    """
