"""
ALICEos - Système d'exploitation virtuel de bureau.

Point d'entrée de l'application. Lance l'écran de démarrage, puis l'écran de connexion,
puis le bureau complet (fond d'écran, barre des tâches, gestion de fenêtres, applications).

Lancement :
    pip install PySide6
    python main.py
"""

import sys
import os

from PySide6.QtWidgets import QApplication, QWidget, QStackedLayout, QVBoxLayout
from PySide6.QtCore import Qt 

from system.settings_manager import SettingsManager
from system.virtual_fs import VirtualFileSystem
from system.window_manager import WindowManager
from system.themes import build_qss

from ui.boot_screen import BootScreen          
from ui.lock_screen import LockScreen
from ui.desktop import Desktop
from ui.taskbar import Taskbar
from ui.notifications import NotificationCenter

from apps.file_explorer import FileExplorer
from apps.terminal import Terminal
from apps.calculator import Calculator
from apps.browser import Browser
from apps.notepad import Notepad
from apps.settings_app import SettingsApp
from apps.task_manager import TaskManager
from apps.bullet_hell import BulletHell

BASE_DIR = os.path.join(os.path.expanduser("~"), ".aliceos")
os.makedirs(BASE_DIR, exist_ok=True)
 

class ALICEos(QWidget):
    """Fenêtre racine unique qui orchestre boot, connexion, verrouillage et bureau."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALICEos")

        self.settings = SettingsManager(BASE_DIR)
        self.vfs = VirtualFileSystem(BASE_DIR)

        self.stack = QStackedLayout(self)
        self.stack.setContentsMargins(0, 0, 0, 0)

        # --- Page 1 : démarrage ---
        self.boot_screen = BootScreen()
        self.boot_screen.finished.connect(self._show_login)
        self.stack.addWidget(self.boot_screen)

        # --- Page 2 : connexion / verrouillage ---
        self.login_screen = LockScreen(self.settings, mode="login")
        self.login_screen.unlocked.connect(self._show_shell)
        self.stack.addWidget(self.login_screen)

        # --- Page 3 : bureau complet ---
        self.shell = QWidget()
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        self.desktop = Desktop(self.settings)
        shell_layout.addWidget(self.desktop, 1)

        self.taskbar = Taskbar(self.settings)
        shell_layout.addWidget(self.taskbar)

        self.stack.addWidget(self.shell)

        # --- Services transverses ---
        self.notifier = NotificationCenter(self.desktop)
        self.wm = WindowManager(self.desktop.mdi, self.taskbar)

        # --- Connexions d'événements ---
        self.taskbar.launch_app.connect(self.open_app)
        self.taskbar.lock_requested.connect(self._show_lock)
        self.desktop.context_action.connect(self._on_desktop_context_action)

        self.apply_theme(self.settings.get("theme", "dark"))

        self.stack.setCurrentWidget(self.boot_screen)

    # --- Transitions entre écrans ---

    def _show_login(self):
        self.stack.setCurrentWidget(self.login_screen)

    def _show_shell(self):
        self.stack.setCurrentWidget(self.shell)
        self.notifier.notify(
            "Bienvenue",
            f"Bonjour {self.settings.get('username', 'Utilisateur')}, ALICEos est prêt.",
        )

    def _show_lock(self):
        lock = LockScreen(self.settings, mode="lock")
        self.stack.addWidget(lock)
        lock.unlocked.connect(lambda: self._unlock(lock))
        self.stack.setCurrentWidget(lock)

    def _unlock(self, lock_widget):
        self.stack.setCurrentWidget(self.shell)
        self.stack.removeWidget(lock_widget)
        lock_widget.deleteLater()

    # --- Thème et fond d'écran ---

    def apply_theme(self, theme_name):
        self.setStyleSheet(build_qss(theme_name))

    # --- Ouverture d'applications ---

    def open_app(self, app_id):
        if app_id == "file_explorer":
            explorer = FileExplorer(self.vfs, self.notifier)
            explorer.open_text_file.connect(self._open_file_in_notepad)
            self.wm.open_window("file_explorer", "Explorateur de fichiers", explorer, "🗂️", size=(680, 440))

        elif app_id == "terminal":
            terminal = Terminal(self.vfs, self.settings)
            self.wm.open_window(f"terminal_{id(terminal)}", "Terminal", terminal, "💻", size=(600, 380))

        elif app_id == "calculator":
            calc = Calculator()
            self.wm.open_window(f"calc_{id(calc)}", "Calculatrice", calc, "🧮", size=(300, 420))

        elif app_id == "browser":
            browser = Browser()
            self.wm.open_window(f"browser_{id(browser)}", "Navigateur", browser, "🌐", size=(700, 480))

        elif app_id == "notepad":
            notepad = Notepad(self.vfs, self.notifier)
            self.wm.open_window(f"notepad_{id(notepad)}", "Bloc-notes", notepad, "📝", size=(560, 420))

        elif app_id == "settings":
            settings_app = SettingsApp(self.settings, self.notifier)
            settings_app.theme_changed.connect(self.apply_theme)
            settings_app.wallpaper_changed.connect(self.desktop.set_wallpaper)
            self.wm.open_window("settings", "Paramètres", settings_app, "⚙️", size=(480, 420))

        elif app_id == "task_manager":
            task_mgr = TaskManager(self.wm)
            self.wm.open_window("task_manager", "Gestionnaire de tâches", task_mgr, "📊", size=(420, 380))

        elif app_id == "bullet_hell":
            game = BulletHell(self.notifier)
            win = self.wm.open_window(f"bullethell_{id(game)}", "Bullet Hell", game, "🌸", size=(760, 560))
            game.setFocus()

        elif app_id == "trash":
            explorer = FileExplorer(self.vfs, self.notifier)
            explorer.current_path = ["Corbeille"]
            explorer._refresh()
            explorer.open_text_file.connect(self._open_file_in_notepad)
            self.wm.open_window("file_explorer", "Corbeille", explorer, "🗑️", size=(680, 440))

    def _open_file_in_notepad(self, folder_path, filename):
        notepad = Notepad(self.vfs, self.notifier, folder_path=list(folder_path), filename=filename)
        self.wm.open_window(f"notepad_{filename}_{id(notepad)}", filename, notepad, "📝", size=(560, 420))

    def _on_desktop_context_action(self, action):
        if action == "open_settings":
            self.open_app("settings")
        elif action == "open_terminal":
            self.open_app("terminal")
        elif action == "new_folder":
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(self, "Nouveau dossier", "Nom du dossier :")
            if ok and name.strip():
                self.vfs.create_folder(["Bureau"], name.strip())
                self.notifier.notify("Dossier créé", f"« {name.strip()} » a été créé sur le Bureau.")
        elif action == "refresh":
            self.desktop.update()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ALICEos")

    window = ALICEos()
    window.showFullScreen()
    window.setCursor(Qt.ArrowCursor)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
