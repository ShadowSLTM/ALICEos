"""
Navigateur web simulé d'ALICEos, avec deux sections multimédias intégrées et un
véritable système d'onglets. Ne se connecte à aucun réseau réel : il affiche des pages
internes fictives, plus deux lecteurs dédiés accessibles par leur propre adresse,
aliceos://video pour les fichiers vidéo du dossier "video", et aliceos://musique pour
les fichiers audio du dossier "musique". Chaque onglet possède son propre lecteur
multimédia indépendant, pour que la lecture dans un onglet n'interfère jamais avec un
autre onglet ouvert en parallèle.
"""

import os
import random
import sys

from PySide6.QtCore import QUrl, Qt, QTime, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

PAGES = {
    "aliceos://accueil": (
        "Accueil",
        "<h2>Bienvenue sur le portail ALICEos</h2>"
        "<p>Ce navigateur est une simulation, il ne se connecte à aucun réseau réel.</p>"
        "<p>Essaie <b>aliceos://video</b>, <b>aliceos://musique</b>, "
        "<b>aliceos://recherche</b> ou <b>aliceos://apropos</b>.</p>",
    ),
    "aliceos://recherche": (
        "Recherche",
        "<h2>Moteur de recherche fictif</h2>"
        "<p>Dans une vraie implémentation, cette page interrogerait un moteur de recherche.</p>"
        "<p>Ici, elle sert uniquement à illustrer la navigation entre pages simulées.</p>",
    ),
    "aliceos://apropos": (
        "À propos",
        "<h2>À propos d'ALICEos</h2>"
        "<p>ALICEos est un système d'exploitation virtuel fonctionnant dans une fenêtre, "
        "conçu comme démonstration technique en Python et PySide6.</p>",
    ),
    "aliceos://video": (
        "Vidéo",
        "<h2>Lecteur vidéo intégré</h2>"
        "<p>Sélectionne un fichier dans le dossier <b>video</b> puis lance la lecture.</p>",
    ),
    "aliceos://musique": (
        "Musique",
        "<h2>Lecteur de musique intégré</h2>"
        "<p>Sélectionne un fichier dans le dossier <b>musique</b> puis lance la lecture, "
        "ou active le mode aléatoire pour enchaîner les pistes dans le désordre.</p>",
    ),
}

VIDEO_EXTENSIONS = (".mp4", ".avi", ".mkv", ".mov", ".webm", ".m4v")
AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a")


def _format_ms(ms):
    """Convertit des millisecondes en texte mm:ss pour l'affichage du temps."""
    t = QTime(0, 0, 0).addMSecs(max(0, ms))
    return t.toString("mm:ss")


class MediaPage(QWidget):
    """
    Base commune aux pages vidéo et musique : liste des fichiers d'un dossier dédié,
    contrôles de lecture, curseur de progression, volume, et mode aléatoire avec
    enchaînement automatique de piste à la fin de chaque lecture.
    """

    def __init__(self, folder_name, extensions, show_video):
        super().__init__()
        self.media_dir = folder_name
        os.makedirs(self.media_dir, exist_ok=True)
        self.extensions = extensions
        self._seeking = False
        self.shuffle_enabled = False

        layout = QVBoxLayout(self)

        if show_video:
            self.video_widget = QVideoWidget()
            # Politique de taille extensible : le widget peut grandir ou rétrécir
            # librement, QVideoWidget conserve nativement les proportions de l'image
            # (bandes noires ajoutées automatiquement) plutôt que de la déformer.
            self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.video_widget.setMinimumSize(160, 90)
            layout.addWidget(self.video_widget, 1)
        else:
            self.video_widget = None
            self.cover_label = QLabel("🎵")
            self.cover_label.setAlignment(Qt.AlignCenter)
            self.cover_label.setStyleSheet("font-size: 64px; color: #9a9ab0;")
            self.cover_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            layout.addWidget(self.cover_label, 1)

        self.info_label = QLabel(f"Dossier surveillé : ./{folder_name}")
        layout.addWidget(self.info_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, 1)

        controls = QHBoxLayout()
        self.play_btn = QPushButton("Lire")
        self.pause_btn = QPushButton("Pause")
        self.stop_btn = QPushButton("Stop")
        self.next_btn = QPushButton("Suivant ▶")
        self.refresh_btn = QPushButton("Rafraîchir")
        controls.addWidget(self.play_btn)
        controls.addWidget(self.pause_btn)
        controls.addWidget(self.stop_btn)
        controls.addWidget(self.next_btn)
        controls.addWidget(self.refresh_btn)
        layout.addLayout(controls)

        # Mode aléatoire : bascule l'enchaînement automatique entre l'ordre de la
        # liste et un tirage aléatoire à chaque fin de piste.
        shuffle_row = QHBoxLayout()
        self.shuffle_btn = QPushButton("🔀 Aléatoire : désactivé")
        self.shuffle_btn.setCheckable(True)
        self.shuffle_btn.toggled.connect(self._on_shuffle_toggled)
        shuffle_row.addWidget(self.shuffle_btn)
        shuffle_row.addStretch()
        layout.addLayout(shuffle_row)

        # Curseur de progression : montre l'avancement et permet de sauter à un
        # instant précis de la vidéo ou de la musique.
        seek_row = QHBoxLayout()
        self.time_current_label = QLabel("00:00")
        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setRange(0, 0)
        self.seek_slider.sliderPressed.connect(self._on_seek_pressed)
        self.seek_slider.sliderReleased.connect(self._on_seek_released)
        self.time_total_label = QLabel("00:00")
        seek_row.addWidget(self.time_current_label)
        seek_row.addWidget(self.seek_slider, 1)
        seek_row.addWidget(self.time_total_label)
        layout.addLayout(seek_row)

        volume_row = QHBoxLayout()
        volume_label = QLabel("Volume")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        volume_row.addWidget(volume_label)
        volume_row.addWidget(self.volume_slider, 1)
        layout.addLayout(volume_row)

        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.7)

        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        if self.video_widget is not None:
            self.player.setVideoOutput(self.video_widget)

        self.play_btn.clicked.connect(self.play_selected)
        self.pause_btn.clicked.connect(self.player.pause)
        self.stop_btn.clicked.connect(self.player.stop)
        self.next_btn.clicked.connect(lambda: self._play_next(auto=False))
        self.refresh_btn.clicked.connect(self.load_files)
        self.list_widget.itemDoubleClicked.connect(lambda _: self.play_selected())
        self.volume_slider.valueChanged.connect(self.change_volume)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        self.load_files()

    # --- Liste des fichiers ---

    def load_files(self):
        self.list_widget.clear()
        try:
            names = os.listdir(self.media_dir)
        except OSError:
            names = []

        files = sorted((n for n in names if n.lower().endswith(self.extensions)), key=str.lower)
        for name in files:
            self.list_widget.addItem(name)

        if not files:
            ext_list = ", ".join(e.lstrip(".") for e in self.extensions)
            self.info_label.setText(f"Aucun fichier compatible trouvé dans ./{self.media_dir} ({ext_list}).")
        else:
            self.info_label.setText(f"{len(files)} fichier(s) trouvé(s) dans ./{self.media_dir}")

    def play_selected(self):
        item = self.list_widget.currentItem()
        if not item:
            self.info_label.setText("Aucun fichier sélectionné.")
            return
        self._play_item(item)

    def _play_item(self, item):
        filename = item.text()
        path = os.path.abspath(os.path.join(self.media_dir, filename))
        if not os.path.exists(path):
            self.info_label.setText("Fichier introuvable.")
            return

        self.list_widget.setCurrentItem(item)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        suffix = " (aléatoire)" if self.shuffle_enabled else ""
        self.info_label.setText(f"Lecture : {filename}{suffix}")

    def change_volume(self, value):
        self.audio_output.setVolume(value / 100.0)

    # --- Mode aléatoire et enchaînement automatique ---

    def _on_shuffle_toggled(self, checked):
        self.shuffle_enabled = checked
        self.shuffle_btn.setText(f"🔀 Aléatoire : {'activé' if checked else 'désactivé'}")

    def _on_media_status_changed(self, status):
        # Dès qu'une piste se termine naturellement, on enchaîne automatiquement,
        # au hasard si le mode aléatoire est actif, sinon dans l'ordre de la liste.
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next(auto=True)

    def _play_next(self, auto):
        count = self.list_widget.count()
        if count == 0:
            return
        current_row = self.list_widget.currentRow()

        if self.shuffle_enabled:
            if count == 1:
                next_row = 0
            else:
                next_row = current_row
                while next_row == current_row:
                    next_row = random.randint(0, count - 1)
        else:
            next_row = current_row + 1
            if next_row >= count:
                if auto:
                    return  # fin de la liste en lecture séquentielle : on n'boucle pas toute seule
                next_row = 0

        item = self.list_widget.item(next_row)
        if item:
            self._play_item(item)

    # --- Curseur de progression ---

    def _on_seek_pressed(self):
        self._seeking = True

    def _on_seek_released(self):
        self._seeking = False
        self.player.setPosition(self.seek_slider.value())

    def _on_position_changed(self, position_ms):
        # Pendant que l'utilisateur fait glisser le curseur, on ne l'écrase pas avec
        # la position réelle du lecteur, sinon il "saute" sous le doigt/la souris.
        if not self._seeking:
            self.seek_slider.setValue(position_ms)
        self.time_current_label.setText(_format_ms(position_ms))

    def _on_duration_changed(self, duration_ms):
        self.seek_slider.setRange(0, duration_ms)
        self.time_total_label.setText(_format_ms(duration_ms))


class VideoPage(MediaPage):
    """Page vidéo : dossier "video", fichiers vidéo uniquement, avec zone d'affichage."""

    def __init__(self):
        super().__init__("video", VIDEO_EXTENSIONS, show_video=True)


class MusicPage(MediaPage):
    """Page musique : dossier "musique", fichiers audio uniquement, sans zone vidéo."""

    def __init__(self):
        super().__init__("musique", AUDIO_EXTENSIONS, show_video=False)


class BrowserTab(QWidget):
    """
    Contenu d'un onglet de navigateur : barre d'adresse, historique, et bascule entre
    les pages HTML simulées et les deux lecteurs multimédias. Chaque onglet crée ses
    propres VideoPage/MusicPage, donc son propre QMediaPlayer indépendant.
    """

    title_changed = Signal(str)

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        toolbar = QHBoxLayout()

        self.back_btn = QPushButton("←")
        self.back_btn.setFixedWidth(36)
        self.back_btn.clicked.connect(self._go_back)
        toolbar.addWidget(self.back_btn)

        self.address_bar = QLineEdit("aliceos://accueil")
        self.address_bar.returnPressed.connect(self._navigate_from_bar)
        toolbar.addWidget(self.address_bar, 1)

        go_btn = QPushButton("Aller")
        go_btn.clicked.connect(self._navigate_from_bar)
        toolbar.addWidget(go_btn)

        layout.addLayout(toolbar)

        self.stack = QStackedWidget()

        self.view = QTextBrowser()
        self.view.setOpenLinks(False)
        self.view.anchorClicked.connect(self._navigate_link)

        self.video_page = VideoPage()
        self.music_page = MusicPage()

        self.stack.addWidget(self.view)
        self.stack.addWidget(self.video_page)
        self.stack.addWidget(self.music_page)

        layout.addWidget(self.stack, 1)

        self.history = []
        self.current_address = None

    def _navigate_from_bar(self):
        self._navigate(self.address_bar.text().strip())

    def _navigate_link(self, url):
        self._navigate(url.toString())

    def _render_html_page(self, address):
        page = PAGES.get(address)

        if page is None:
            return (
                f"<h2>Page introuvable</h2>"
                f"<p>« {address} » n'existe pas dans ce navigateur simulé.</p>"
                "<p><a href='aliceos://accueil'>Retour à l'accueil</a></p>"
            )

        title, html = page
        links = "".join(
            f"<p><a href='{addr}'>{addr}</a></p>" for addr in PAGES if addr != address
        )
        return html + "<hr>" + links

    def _navigate(self, address, add_to_history=True):
        if not address:
            return

        if add_to_history and self.current_address is not None:
            self.history.append(self.current_address)

        self.current_address = address
        self.address_bar.setText(address)

        if address == "aliceos://video":
            self.stack.setCurrentWidget(self.video_page)
            self.video_page.load_files()
        elif address == "aliceos://musique":
            self.stack.setCurrentWidget(self.music_page)
            self.music_page.load_files()
        else:
            self.stack.setCurrentWidget(self.view)
            self.view.setHtml(self._render_html_page(address))

        page = PAGES.get(address)
        self.title_changed.emit(page[0] if page else "Page introuvable")

    def _go_back(self):
        if not self.history:
            return

        previous = self.history.pop()
        self._navigate(previous, add_to_history=False)


class Browser(QWidget):
    """
    Fenêtre du navigateur ALICEos, avec un vrai système d'onglets : chaque onglet est
    un BrowserTab indépendant, un bouton "+" permet d'en ouvrir un nouveau, et les
    onglets se ferment individuellement (en gardant toujours au moins un onglet ouvert).
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALICEos Browser")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self._close_tab)

        new_tab_btn = QPushButton("+")
        new_tab_btn.setFixedSize(28, 24)
        new_tab_btn.setToolTip("Nouvel onglet")
        new_tab_btn.clicked.connect(lambda: self._add_tab())
        self.tabs.setCornerWidget(new_tab_btn, Qt.TopRightCorner)

        layout.addWidget(self.tabs)

        self._add_tab("aliceos://accueil")

    def _add_tab(self, address="aliceos://accueil"):
        tab = BrowserTab()
        index = self.tabs.addTab(tab, "Nouvel onglet")
        tab.title_changed.connect(lambda title, t=tab: self._update_tab_title(t, title))
        self.tabs.setCurrentIndex(index)
        tab._navigate(address, add_to_history=False)
        return tab

    def _update_tab_title(self, tab, title):
        index = self.tabs.indexOf(tab)
        if index >= 0:
            short = title if len(title) <= 18 else title[:17] + "…"
            self.tabs.setTabText(index, short)

    def _close_tab(self, index):
        if self.tabs.count() <= 1:
            return  # toujours garder au moins un onglet ouvert, comme un vrai navigateur
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        widget.deleteLater()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    browser = Browser()
    browser.resize(900, 650)
    browser.show()
    sys.exit(app.exec())