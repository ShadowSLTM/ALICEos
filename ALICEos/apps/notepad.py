"""
Bloc-notes d'ALICEos.
Édite un fichier texte du système de fichiers virtuel, ou un document volant non encore
rattaché à un fichier si ouvert depuis le menu Démarrer. Présentation façon traitement
de texte : une page blanche à bords fixes, centrée sur un fond gris, avec du texte noir
et des marges, plutôt qu'une simple zone de texte qui occupe toute la fenêtre.

Qt ne pagine pas automatiquement un QTextEdit (fixer une taille de page sur le document
n'a aucun effet visuel dans un éditeur), donc le système de pages est simulé à la main :
des traits de séparation sont dessinés par-dessus le texte à intervalles réguliers pour
matérialiser les sauts de page, et le numéro de page affiché dans la barre d'outils est
calculé à partir de la position verticale du curseur dans le document.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QLabel
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QFont, QPainter, QColor, QPen

PAGE_WIDTH = 650
PAGE_HEIGHT = 840
PAGE_MARGIN = 60
PAGE_GAP = 24  # espace gris visible entre deux pages, comme dans un traitement de texte


class PageTextEdit(QTextEdit):
    """
    QTextEdit habillé pour ressembler à une page de document : fond blanc, texte noir,
    marges confortables, et des séparations de page dessinées par-dessus le contenu à
    intervalles réguliers pour simuler la pagination.
    """

    def __init__(self):
        super().__init__()
        self.setFixedWidth(PAGE_WIDTH)
        self.document().setDocumentMargin(PAGE_MARGIN)
        self.setFrameShape(QTextEdit.NoFrame)
        self.setStyleSheet(
            "QTextEdit {"
            "  background-color: #ffffff;"
            "  color: #1a1a1a;"
            "  font-family: 'Calibri', 'Segoe UI', sans-serif;"
            "  font-size: 14px;"
            "  border: none;"
            "}"
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        self._draw_page_breaks()

    def _draw_page_breaks(self):
        """Dessine une bande grise à chaque saut de page, pour matérialiser la fin d'une
        page et le début de la suivante, comme dans la vue continue d'un traitement de texte."""
        scroll_offset = self.verticalScrollBar().value()
        viewport_height = self.viewport().height()

        painter = QPainter(self.viewport())
        painter.setPen(Qt.NoPen)

        page_bottom = PAGE_HEIGHT
        while page_bottom - scroll_offset < viewport_height:
            y = page_bottom - scroll_offset
            if y + PAGE_GAP > 0:
                painter.setBrush(QColor("#c8c8cc"))
                painter.drawRect(QRectF(0, y, self.viewport().width(), PAGE_GAP))
                painter.setPen(QPen(QColor("#9a9aa4"), 1))
                painter.drawLine(0, int(y), self.viewport().width(), int(y))
                painter.drawLine(0, int(y + PAGE_GAP), self.viewport().width(), int(y + PAGE_GAP))
                painter.setPen(Qt.NoPen)
            page_bottom += PAGE_HEIGHT + PAGE_GAP
        painter.end()

    def current_page_number(self):
        """Numéro de la page où se trouve le curseur, à partir de sa position verticale
        dans le document (chaque page occupe PAGE_HEIGHT + PAGE_GAP pixels de hauteur)."""
        cursor_top = self.cursorRect().top() + self.verticalScrollBar().value()
        return int(cursor_top // (PAGE_HEIGHT + PAGE_GAP)) + 1

    def total_pages(self):
        """Nombre total de pages, à partir de la hauteur totale du document (la marge
        est déjà comprise dans document().size().height(), inutile de l'ajouter encore)."""
        doc_height = self.document().size().height()
        return max(1, int(doc_height // (PAGE_HEIGHT + PAGE_GAP)) + 1)


class Notepad(QWidget):
    def __init__(self, vfs, notifier=None, folder_path=None, filename=None):
        super().__init__()
        self.vfs = vfs
        self.notifier = notifier
        self.folder_path = folder_path
        self.filename = filename

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(10, 8, 10, 8)
        self.title_label = QLabel(filename or "Document sans titre")
        self.title_label.setStyleSheet("font-weight: 600;")
        toolbar.addWidget(self.title_label, 1)

        self.page_label = QLabel("Page 1 / 1")
        self.page_label.setStyleSheet("color: #9a9ab0;")
        toolbar.addWidget(self.page_label)

        save_btn = QPushButton("Enregistrer")
        save_btn.clicked.connect(self.save)
        toolbar.addWidget(save_btn)
        layout.addLayout(toolbar)

        # Fond gris englobant, dans lequel la page blanche reste centrée quelle que
        # soit la largeur de la fenêtre, comme dans un vrai traitement de texte.
        page_backdrop = QWidget()
        page_backdrop.setStyleSheet("background-color: #6e6e78;")
        backdrop_layout = QHBoxLayout(page_backdrop)
        backdrop_layout.setContentsMargins(0, 20, 0, 20)
        backdrop_layout.setAlignment(Qt.AlignHCenter)

        self.editor = PageTextEdit()
        if folder_path is not None and filename:
            node = self.vfs.resolve(folder_path + [filename])
            if node and not node.is_dir:
                self.editor.setPlainText(node.content)
        self.editor.textChanged.connect(self._update_page_label)
        self.editor.cursorPositionChanged.connect(self._update_page_label)
        backdrop_layout.addWidget(self.editor)

        layout.addWidget(page_backdrop, 1)

        self._update_page_label()

    def _update_page_label(self):
        current = self.editor.current_page_number()
        total = self.editor.total_pages()
        current = min(current, total)
        self.page_label.setText(f"Page {current} / {total}")
        self.editor.viewport().update()

    def save(self):
        if self.folder_path is not None and self.filename:
            self.vfs.write_file(self.folder_path, self.filename, self.editor.toPlainText())
            if self.notifier:
                self.notifier.notify("Enregistré", f"« {self.filename} » a été enregistré.")
        else:
            if self.notifier:
                self.notifier.notify("Astuce", "Ouvre ce document depuis l'explorateur pour l'enregistrer sur un fichier.")
