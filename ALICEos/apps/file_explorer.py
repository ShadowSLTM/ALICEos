"""
Explorateur de fichiers d'ALICEos.
Navigue dans le système de fichiers virtuel partagé (VirtualFileSystem), avec
volet latéral de raccourcis, fil d'ariane, création de fichiers/dossiers,
renommage, suppression vers la corbeille, et ouverture des fichiers texte dans le Bloc-notes.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem, QLabel,
    QPushButton, QLineEdit, QInputDialog, QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QAction


SHORTCUTS = ["Ce PC", "Bureau", "Documents", "Images", "Téléchargements", "Corbeille"]


class FileExplorer(QWidget):
    """Fenêtre d'exploration du système de fichiers virtuel."""

    open_text_file = Signal(list, str)  # (chemin du dossier parent, nom du fichier)

    def __init__(self, vfs, notifier=None):
        super().__init__()
        self.vfs = vfs
        self.notifier = notifier
        self.current_path = []  # liste de segments depuis la racine "Ce PC"

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Volet latéral des raccourcis
        sidebar = QWidget()
        sidebar.setFixedWidth(140)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(8, 10, 8, 10)
        sb_layout.setSpacing(2)
        self.sidebar_list = QListWidget()
        self.sidebar_list.addItems(SHORTCUTS)
        self.sidebar_list.itemClicked.connect(self._go_shortcut)
        sb_layout.addWidget(QLabel("Raccourcis"))
        sb_layout.addWidget(self.sidebar_list)
        root_layout.addWidget(sidebar)

        # Zone principale
        main_area = QWidget()
        main_layout = QVBoxLayout(main_area)
        main_layout.setContentsMargins(10, 10, 10, 10)

        toolbar = QHBoxLayout()
        self.back_btn = QPushButton("←")
        self.back_btn.setFixedWidth(36)
        self.back_btn.clicked.connect(self._go_back)
        toolbar.addWidget(self.back_btn)

        self.path_label = QLabel("Ce PC")
        self.path_label.setStyleSheet("font-weight: 600;")
        toolbar.addWidget(self.path_label, 1)

        new_folder_btn = QPushButton("Nouveau dossier")
        new_folder_btn.clicked.connect(self._new_folder)
        toolbar.addWidget(new_folder_btn)

        new_file_btn = QPushButton("Nouveau fichier")
        new_file_btn.clicked.connect(self._new_file)
        toolbar.addWidget(new_file_btn)

        main_layout.addLayout(toolbar)

        self.file_list = QListWidget()
        self.file_list.setViewMode(QListWidget.IconMode)
        self.file_list.setResizeMode(QListWidget.Adjust)
        self.file_list.setGridSize(QSize(96, 84))
        self.file_list.setSpacing(8)
        self.file_list.itemDoubleClicked.connect(self._open_item)
        self.file_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.file_list.customContextMenuRequested.connect(self._context_menu)
        main_layout.addWidget(self.file_list)

        root_layout.addWidget(main_area, 1)

        self._refresh()

    # --- Navigation ---

    def _go_shortcut(self, item):
        name = item.text()
        self.current_path = [] if name == "Ce PC" else [name]
        self._refresh()

    def _go_back(self):
        if self.current_path:
            self.current_path.pop()
            self._refresh()

    def _open_item(self, item):
        name = item.data(Qt.UserRole)
        node = self.vfs.resolve(self.current_path + [name])
        if node is None:
            return
        if node.is_dir:
            self.current_path.append(name)
            self._refresh()
        else:
            self.open_text_file.emit(list(self.current_path), name)

    def _refresh(self):
        self.path_label.setText("Ce PC" + ("".join(f" / {p}" for p in self.current_path)))
        self.file_list.clear()
        for node in self.vfs.list_dir(self.current_path):
            icon = "📁" if node.is_dir else "📄"
            item = QListWidgetItem(f"{icon}\n{node.name}")
            item.setData(Qt.UserRole, node.name)
            item.setTextAlignment(Qt.AlignCenter)
            self.file_list.addItem(item)

    # --- Actions ---

    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
        if ok and name.strip():
            if self.vfs.create_folder(self.current_path, name.strip()):
                self._refresh()
                self._toast("Dossier créé", f"« {name.strip()} » a été créé.")

    def _new_file(self):
        name, ok = QInputDialog.getText(self, "Nouveau fichier", "Nom du fichier (avec extension) :")
        if ok and name.strip():
            if self.vfs.create_file(self.current_path, name.strip()):
                self._refresh()
                self._toast("Fichier créé", f"« {name.strip()} » a été créé.")

    def _context_menu(self, pos):
        item = self.file_list.itemAt(pos)
        menu = QMenu(self)
        if item:
            name = item.data(Qt.UserRole)
            open_action = QAction("Ouvrir", self)
            open_action.triggered.connect(lambda: self._open_item(item))
            menu.addAction(open_action)

            rename_action = QAction("Renommer", self)
            rename_action.triggered.connect(lambda: self._rename(name))
            menu.addAction(rename_action)

            delete_action = QAction("Déplacer vers la corbeille", self)
            delete_action.triggered.connect(lambda: self._delete(name))
            menu.addAction(delete_action)
        else:
            new_folder_action = QAction("Nouveau dossier", self)
            new_folder_action.triggered.connect(self._new_folder)
            menu.addAction(new_folder_action)
            new_file_action = QAction("Nouveau fichier", self)
            new_file_action.triggered.connect(self._new_file)
            menu.addAction(new_file_action)
        menu.exec(self.file_list.mapToGlobal(pos))

    def _rename(self, old_name):
        new_name, ok = QInputDialog.getText(self, "Renommer", "Nouveau nom :", text=old_name)
        if ok and new_name.strip() and new_name != old_name:
            if self.vfs.rename(self.current_path, old_name, new_name.strip()):
                self._refresh()

    def _delete(self, name):
        if self.current_path == ["Corbeille"]:
            confirm = QMessageBox.question(self, "Supprimer définitivement",
                                            f"Supprimer définitivement « {name} » ?")
            if confirm == QMessageBox.Yes:
                self.vfs.delete_permanently(self.current_path, name)
                self._refresh()
        else:
            self.vfs.delete_to_trash(self.current_path, name)
            self._refresh()
            self._toast("Déplacé vers la corbeille", f"« {name} » a été déplacé vers la corbeille.")

    def _toast(self, title, message):
        if self.notifier:
            self.notifier.notify(title, message)
