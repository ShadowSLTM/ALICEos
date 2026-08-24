"""
Terminal intégré d'ALICEos.
Interprète un petit jeu de commandes (ls, cd, cat, mkdir, touch, rm, echo, whoami,
date, help, clear, quit) qui opèrent directement sur le système de fichiers virtuel
partagé, plus une poignée de commandes cachées sans autre utilité que de faire sourire
(clins d'œil à Linux et à quelques animes), listées séparément dans l'aide.
"""

import random

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QTextEdit, QLineEdit
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QFont


MONOKUMA_LINES = [
    "Upupupu... Un peu de désespoir donne tellement plus de saveur à l'espoir, tu ne trouves pas ?",
    "Tiens tiens, quelqu'un explore le terminal au lieu de dormir. Puni-shed !",
    "L'espoir et le désespoir, c'est un peu comme le sucre et le sel dans un bon gâteau au chocolat.",
    "Ce terminal n'est pas une salle de classe, mais je garde quand même un œil sur toi. Upupupu.",
]

HERO_LINES = [
    "PLUS ULTRA !!! Même un terminal mérite qu'on lui donne tout ce qu'on a !",
    "Un vrai héros ne recule jamais devant une ligne de commande mal formée.",
    "Detroit Smash... version clavier : cette touche Entrée n'a rien vu venir.",
    "Ce n'est pas la taille du programme qui compte, c'est le nombre de fois où tu te relèves après un bug.",
]

ANIME_LINES = [
    "Le héros crie le nom de sa prochaine commande avant de l'exécuter. C'est plus stylé comme ça.",
    "Générique d'ouverture lancé. Courage, détermination, et beaucoup trop d'exclamations.",
    "Flash-back inutile de douze secondes pendant que la commande précédente finit de charger.",
    "Un rival mystérieux vient d'installer le même OS que toi, juste pour te défier.",
    "La commande la plus puissante n'est jamais celle qu'on utilise en premier.",
]


class Terminal(QWidget):
    def __init__(self, vfs, settings, on_open_app=None):
        super().__init__()
        self.vfs = vfs
        self.settings = settings
        self.on_open_app = on_open_app
        self.cwd = []  # chemin courant dans le vfs

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        mono = QFont("Consolas", 11)
        self.output.setFont(mono)
        self.output.setStyleSheet("background-color: #0d0e14; color: #9df08a; border: none; padding: 8px;")
        layout.addWidget(self.output)

        self.input = QLineEdit()
        self.input.setFont(mono)
        self.input.setStyleSheet("background-color: #14151d; color: #f2f2f7; border: none; padding: 8px;")
        self.input.returnPressed.connect(self._run_command)
        layout.addWidget(self.input)

        self._print("ALICEos Terminal v1.0")
        self._print("Tape 'help' pour la liste des commandes disponibles.\n")
        self.input.setFocus()

    def _prompt(self):
        path = "~/" + "/".join(self.cwd) if self.cwd else "~"
        return f"{self.settings.get('username', 'user').lower()}@aliceos:{path}$ "

    def _print(self, text=""):
        self.output.append(text)

    def _run_command(self):
        raw = self.input.text().strip()
        self.input.clear()
        if not raw:
            return
        self._print(self._prompt() + raw)
        parts = raw.split()
        cmd, args = parts[0], parts[1:]

        handlers = {
            "help": self._cmd_help,
            "ls": self._cmd_ls,
            "cd": self._cmd_cd,
            "cat": self._cmd_cat,
            "mkdir": self._cmd_mkdir,
            "touch": self._cmd_touch,
            "rm": self._cmd_rm,
            "echo": self._cmd_echo,
            "whoami": self._cmd_whoami,
            "date": self._cmd_date,
            "clear": self._cmd_clear,
            "pwd": self._cmd_pwd,
            "quit": self._cmd_quit,
            # --- commandes cachées, juste pour le plaisir ---
            "hello": self._cmd_hello,
            "sudo": self._cmd_sudo,
            "neofetch": self._cmd_neofetch,
            "monokuma": self._cmd_monokuma,
            "plusultra": self._cmd_plusultra,
            "anime": self._cmd_anime,
        }
        handler = handlers.get(cmd)
        if handler:
            handler(args)
        else:
            self._print(f"Commande introuvable : {cmd}. Tape 'help' pour la liste des commandes.")

    def _cmd_help(self, args):
        self._print(
            "Commandes disponibles :\n"
            "  ls              liste le contenu du dossier courant\n"
            "  cd <dossier>    change de dossier (cd .. pour remonter)\n"
            "  cat <fichier>   affiche le contenu d'un fichier texte\n"
            "  mkdir <nom>     crée un dossier\n"
            "  touch <nom>     crée un fichier vide\n"
            "  rm <nom>        déplace un élément vers la corbeille\n"
            "  echo <texte>    affiche du texte\n"
            "  whoami          affiche l'utilisateur courant\n"
            "  date            affiche la date et l'heure\n"
            "  pwd             affiche le chemin courant\n"
            "  clear           efface l'écran\n"
            "  quit            quitter ALICEos\n"
            "\n"
            "Il paraît aussi qu'il existe quelques commandes cachées dans ce terminal...\n"
            "à toi de les trouver. 🔍"
        )

    def _cmd_ls(self, args):
        nodes = self.vfs.list_dir(self.cwd)
        if not nodes:
            self._print("(dossier vide)")
            return
        self._print("  ".join((n.name + "/") if n.is_dir else n.name for n in nodes))

    def _cmd_cd(self, args):
        if not args:
            self.cwd = []
            return
        target = args[0]
        if target == "..":
            if self.cwd:
                self.cwd.pop()
            return
        if target in ("~", "/"):
            self.cwd = []
            return
        node = self.vfs.resolve(self.cwd + [target])
        if node and node.is_dir:
            self.cwd.append(target)
        else:
            self._print(f"cd : dossier introuvable : {target}")

    def _cmd_cat(self, args):
        if not args:
            self._print("Usage : cat <fichier>")
            return
        node = self.vfs.resolve(self.cwd + [args[0]])
        if node and not node.is_dir:
            self._print(node.content or "(fichier vide)")
        else:
            self._print(f"cat : fichier introuvable : {args[0]}")

    def _cmd_mkdir(self, args):
        if not args:
            self._print("Usage : mkdir <nom>")
            return
        if self.vfs.create_folder(self.cwd, args[0]):
            self._print(f"Dossier créé : {args[0]}")
        else:
            self._print("Impossible de créer ce dossier (nom déjà utilisé ?).")

    def _cmd_touch(self, args):
        if not args:
            self._print("Usage : touch <nom>")
            return
        if self.vfs.create_file(self.cwd, args[0]):
            self._print(f"Fichier créé : {args[0]}")
        else:
            self._print("Impossible de créer ce fichier (nom déjà utilisé ?).")

    def _cmd_rm(self, args):
        if not args:
            self._print("Usage : rm <nom>")
            return
        # Clin d'œil Linux : la commande la plus tristement célèbre du monde Unix,
        # ici totalement inoffensive puisqu'on ne touche jamais au vrai disque.
        if args[0:1] == ["-rf"] and len(args) > 1 and args[1] == "/":
            self._print("Belle tentative. Même en root, ce terminal ne touchera jamais ton vrai disque. Upupupu.")
            return
        if self.vfs.delete_to_trash(self.cwd, args[0]):
            self._print(f"Déplacé vers la corbeille : {args[0]}")
        else:
            self._print(f"rm : élément introuvable : {args[0]}")

    def _cmd_echo(self, args):
        self._print(" ".join(args))

    def _cmd_whoami(self, args):
        self._print(self.settings.get("username", "utilisateur"))

    def _cmd_date(self, args):
        self._print(QDateTime.currentDateTime().toString("dddd d MMMM yyyy, HH:mm:ss"))

    def _cmd_pwd(self, args):
        self._print("~/" + "/".join(self.cwd) if self.cwd else "~")

    def _cmd_clear(self, args):
        self.output.clear()

    def _cmd_quit(self, args):
        app = QApplication.instance()
        if app:
            app.quit()

    # --- Commandes cachées ---

    def _cmd_hello(self, args):
        self._print("Hello, world! (le tout premier programme, encore et toujours le meilleur)")

    def _cmd_sudo(self, args):
        if not args:
            self._print("Usage : sudo <commande>")
            return
        user = self.settings.get("username", "utilisateur")
        self._print(f"[sudo] mot de passe pour {user} : ")
        self._print(f"{user} n'est pas dans le fichier sudoers. Cet incident sera signalé. (mais pas vraiment, c'est pour rire)")

    def _cmd_neofetch(self, args):
        user = self.settings.get("username", "utilisateur").lower()
        self._print(
            "        _.-,\n"
            "     .-'  /   ALICEos v1.0\n"
            "     '-.  \\   ------------\n"
            f"        '-,_\\  Utilisateur : {user}\n"
            "               Noyau       : aucun (voir la FAQ)\n"
            "               Shell       : ALICEos Terminal\n"
            "               Moteur      : Python + PySide6\n"
            "               Thème       : " + str(self.settings.get("theme", "sombre"))
        )

    def _cmd_monokuma(self, args):
        self._print(random.choice(MONOKUMA_LINES))

    def _cmd_plusultra(self, args):
        self._print(random.choice(HERO_LINES))

    def _cmd_anime(self, args):
        self._print(random.choice(ANIME_LINES))
