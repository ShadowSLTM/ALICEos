"""
Bullet Hell - jeu par défaut d'ALICEos (aux côtés de Doom Mini).
Un shoot 'em up vertical façon Touhou : le joueur esquive des motifs de tirs colorés,
abat des vagues d'ennemis, puis affronte un boss à plusieurs phases par niveau. Seize
niveaux, chacun avec sa propre palette de couleurs et son propre boss.

Cette version ajoute un seizième niveau, épilogue au-delà du trône du vampire originel,
et un vrai sélecteur de difficulté (Facile / Normal / Difficile) choisi sur l'écran
titre avec les flèches gauche/droite, qui ajuste les vies et bombes de départ, les PV
des boss, la vitesse de leurs tirs, et la résistance des ennemis de vague.

Elle conserve le pool de dix motifs de tir avec une combinaison propre à chaque boss,
l'écran titre, le menu interactif entre chaque niveau (continuer, sauvegarder, retour
au titre), la musique de fond chargée depuis de vrais fichiers mp3 posés dans le dossier
assets/ost, et la sauvegarde de la progression en JSON (qui retient aussi la difficulté
choisie).

Entièrement autonome, rendu à la main avec QPainter, aucune dépendance externe au-delà
de PySide6 déjà utilisé partout ailleurs dans ALICEos (QtMultimedia pour l'OST, déjà
utilisé par le lecteur vidéo/musique du navigateur).
"""

import json
import math
import os
import random
import time

from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, QUrl
from PySide6.QtGui import QPainter, QColor, QFont, QPen, QBrush
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput

# --- Dimensions logiques de l'arène de jeu (letterboxées dans le widget, voir paintEvent) ---
PLAY_W = 420
PLAY_H = 600
HUD_W = 170

# Réglages de base (niveau de difficulté "Normal") : vaisseau rapide, vies et bombes de
# départ généreuses, invincibilité assez longue après un coup. Le sélecteur de
# difficulté (voir DIFFICULTIES plus bas) vient ensuite moduler certains de ces nombres.
PLAYER_SPEED_NORMAL = 280.0
PLAYER_SPEED_FOCUS = 140.0
PLAYER_HIT_RADIUS = 3.0
PLAYER_SPRITE_RADIUS = 9.0
PLAYER_FIRE_INTERVAL = 0.08
PLAYER_BULLET_SPEED = 460.0
PLAYER_BULLET_DAMAGE = 3
INVINCIBLE_DURATION = 2.5
STARTING_LIVES = 12
STARTING_BOMBS = 5

# --- Niveaux de difficulté ---
# lives/bombs : décalage additif par rapport à STARTING_LIVES / STARTING_BOMBS (jamais
# en dessous de 1 vie et 0 bombe, voir _start_new_game).
# hp_mult : multiplie les PV du boss du niveau.
# bonus_mult : multiplie le bonus de vitesse par niveau des tirs de boss (voir
# Boss.update, difficulty_bonus = level_index * 6 * bonus_mult).
# trash_hp_mult / trash_speed_mult : multiplient les PV et la vitesse des ennemis de vague.
DIFFICULTIES = [
    {"label": "Facile", "lives": 5, "bombs": 2, "hp_mult": 0.7, "bonus_mult": 0.7, "trash_hp_mult": 0.7, "trash_speed_mult": 0.85},
    {"label": "Normal", "lives": 0, "bombs": 0, "hp_mult": 1.0, "bonus_mult": 1.0, "trash_hp_mult": 1.0, "trash_speed_mult": 1.0},
    {"label": "Difficile", "lives": -5, "bombs": -2, "hp_mult": 1.4, "bonus_mult": 1.35, "trash_hp_mult": 1.3, "trash_speed_mult": 1.2},
]
DEFAULT_DIFFICULTY_INDEX = 1  # Normal

# --- Dossier de musiques (OST) et fichier de sauvegarde, à côté du dossier ALICEos ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OST_DIR = os.path.join(_PROJECT_ROOT, "assets", "ost")
SAVE_PATH = os.path.join(_PROJECT_ROOT, "assets", "bullet_hell_save.json")
TITLE_OST = "titre.mp3"
TITLE_BG_TOP, TITLE_BG_BOTTOM = "#0a0a18", "#171034"


def _ensure_ost_dir():
    os.makedirs(OST_DIR, exist_ok=True)
    readme_path = os.path.join(OST_DIR, "LISEZ-MOI.txt")
    if not os.path.exists(readme_path):
        try:
            with open(readme_path, "w", encoding="utf-8") as f:
                f.write(
                    "Dépose ici tes fichiers mp3 pour la musique de fond du jeu.\n\n"
                    "Noms attendus :\n"
                    "  titre.mp3     joué sur l'écran titre et le menu entre les niveaux\n"
                    "  niveau1.mp3 ... niveau16.mp3   un morceau par niveau (vague + boss)\n\n"
                    "Un fichier manquant ne bloque rien : le jeu reste silencieux pour ce niveau."
                )
        except OSError:
            pass


# Seize niveaux. Chaque palette a été retravaillée pour que deux niveaux qui se suivent
# ne se ressemblent jamais, les PV des boss montent sur toute la ligne, et la clé
# "patterns" donne à chaque boss ses trois motifs de tir personnels (un par phase de
# vie), piochés dans le pool de dix motifs défini plus bas (voir PATTERN_FUNCS). Les
# nombres ci-dessous sont ceux du niveau de difficulté "Normal" ; voir DIFFICULTIES
# pour la façon dont ils sont ajustés selon le mode choisi.
LEVELS = [
    {
        "name": "Niveau 1 — Jardin Écarlate",
        "bg_top": "#2b0a12", "bg_bottom": "#7a1030",
        "trash_color": "#ff5c8a", "trash_hp": 1, "trash_count": 20, "trash_interval": 1.35,
        "boss_name": "Yoruha Tsukikage, Aile de la Lune Noire", "boss_color": "#ff2d55", "boss_hp": 600,
        "ost": "niveau1.mp3", "patterns": ["radial", "aimed", "spiral"],
    },
    {
        "name": "Niveau 2 — Temple des Fleurs Noires",
        "bg_top": "#1c0a24", "bg_bottom": "#4a0f66",
        "trash_color": "#d966ff", "trash_hp": 2, "trash_count": 20, "trash_interval": 1.25,
        "boss_name": "Kurohana Reika, Fleur des Ténèbres", "boss_color": "#b026ff", "boss_hp": 660,
        "ost": "niveau2.mp3", "patterns": ["aimed", "flower", "spiral"],
    },
    {
        "name": "Niveau 3 — Palais de Glace Éternelle",
        "bg_top": "#0c1a2e", "bg_bottom": "#2d4d7a",
        "trash_color": "#7fdcff", "trash_hp": 2, "trash_count": 20, "trash_interval": 1.15,
        "boss_name": "Akane Shiroyuki, Neige Écarlate", "boss_color": "#005586", "boss_hp": 720,
        "ost": "niveau3.mp3", "patterns": ["radial", "wave", "aimed"],
    },
    {
        "name": "Niveau 4 — Brume des Ombres",
        "bg_top": "#0e131c", "bg_bottom": "#2b3550",
        "trash_color": "#9fb3ff", "trash_hp": 2, "trash_count": 20, "trash_interval": 1.05,
        "boss_name": "Miyako Yamikiri, Reine des Brumes", "boss_color": "#5c6fff", "boss_hp": 780,
        "ost": "niveau4.mp3", "patterns": ["wall", "aimed", "spiral"],
    },
    {
        "name": "Niveau 5 — Royaume des Cerisiers Maudits",
        "bg_top": "#2b0e22", "bg_bottom": "#7a1f52",
        "trash_color": "#ff8fc7", "trash_hp": 3, "trash_count": 20, "trash_interval": 0.95,
        "boss_name": "Sakura Kuronami, Vampire du Cerisier Noir", "boss_color": "#ff2f88", "boss_hp": 840,
        "ost": "niveau5.mp3", "patterns": ["flower", "aimed", "double_spiral"],
    },
    {
        "name": "Niveau 6 — Sanctuaire Lunaire",
        "bg_top": "#0a0e26", "bg_bottom": "#2e3480",
        "trash_color": "#c7c7ff", "trash_hp": 3, "trash_count": 20, "trash_interval": 0.85,
        "boss_name": "Ayame Tsukishiro, Gardienne de la Lune", "boss_color": "#9fb0ff", "boss_hp": 900,
        "ost": "niveau6.mp3", "patterns": ["radial", "wall", "wave"],
    },
    {
        "name": "Niveau 7 — Royaume des Âmes Perdues",
        "bg_top": "#0a0c1c", "bg_bottom": "#401a66",
        "trash_color": "#a366ff", "trash_hp": 3, "trash_count": 20, "trash_interval": 0.80,
        "boss_name": "Rei Amatsuki, Effaceuse de Souvenirs", "boss_color": "#7a1fff", "boss_hp": 960,
        "ost": "niveau7.mp3", "patterns": ["scatter", "spiral", "pincer"],
    },
    {
        "name": "Niveau 8 — Nuages Sanglants",
        "bg_top": "#2b0a08", "bg_bottom": "#7a1810",
        "trash_color": "#ff5533", "trash_hp": 3, "trash_count": 20, "trash_interval": 0.75,
        "boss_name": "Shion Akagumo, Nuage Rouge", "boss_color": "#ff1a1a", "boss_hp": 1020,
        "ost": "niveau8.mp3", "patterns": ["aimed", "cross", "spiral"],
    },
    {
        "name": "Niveau 9 — Jardin de la Rose Noire",
        "bg_top": "#1a0510", "bg_bottom": "#4d0022",
        "trash_color": "#ff5c9e", "trash_hp": 4, "trash_count": 20, "trash_interval": 0.70,
        "boss_name": "Natsumi Kurobara, Rose Noire", "boss_color": "#c2003d", "boss_hp": 1080,
        "ost": "niveau9.mp3", "patterns": ["wave", "pincer", "flower"],
    },
    {
        "name": "Niveau 10 — Pluie de Minuit",
        "bg_top": "#05141c", "bg_bottom": "#114a5c",
        "trash_color": "#55e0ff", "trash_hp": 4, "trash_count": 20, "trash_interval": 0.65,
        "boss_name": "Hanae Yoruame, Danseuse de la Pluie", "boss_color": "#00d4ff", "boss_hp": 1140,
        "ost": "niveau10.mp3", "patterns": ["radial", "scatter", "double_spiral"],
    },
    {
        "name": "Niveau 11 — Lac des Reflets Noirs",
        "bg_top": "#04201c", "bg_bottom": "#0a4a3a",
        "trash_color": "#4de0b0", "trash_hp": 4, "trash_count": 20, "trash_interval": 0.60,
        "boss_name": "Kira Mizukage, Ombre de l'Eau", "boss_color": "#00b386", "boss_hp": 1200,
        "ost": "niveau11.mp3", "patterns": ["wall", "flower", "cross"],
    },
    {
        "name": "Niveau 12 — Château de Glace Éternelle",
        "bg_top": "#0c1c33", "bg_bottom": "#3d6fa3",
        "trash_color": "#d6f2ff", "trash_hp": 5, "trash_count": 20, "trash_interval": 0.55,
        "boss_name": "Emi Fuyutsuki, Lune d'Hiver", "boss_color": "#7fd4ff", "boss_hp": 1260,
        "ost": "niveau12.mp3", "patterns": ["cross", "aimed", "double_spiral"],
    },
    {
        "name": "Niveau 13 — Forêt des Corbeaux",
        "bg_top": "#06080a", "bg_bottom": "#1c2418",
        "trash_color": "#6a5c99", "trash_hp": 5, "trash_count": 20, "trash_interval": 0.50,
        "boss_name": "Nozomi Karasuhime, Princesse Corbeau", "boss_color": "#8877ff", "boss_hp": 1320,
        "ost": "niveau13.mp3", "patterns": ["scatter", "wave", "spiral"],
    },
    {
        "name": "Niveau 14 — Forge du Sang Noir",
        "bg_top": "#1c0704", "bg_bottom": "#5c1400",
        "trash_color": "#ff7733", "trash_hp": 5, "trash_count": 20, "trash_interval": 0.45,
        "boss_name": "Valeria Kurogane, Acier Vampire", "boss_color": "#ff3300", "boss_hp": 1380,
        "ost": "niveau14.mp3", "patterns": ["pincer", "radial", "cross"],
    },
    {
        "name": "Niveau 15 — Trône du Vampire Originel",
        "bg_top": "#08000c", "bg_bottom": "#471d00",
        "trash_color": "#ffcc33", "trash_hp": 6, "trash_count": 20, "trash_interval": 0.40,
        "boss_name": "Rena Yoruha, Souveraine de la Nuit Éternelle", "boss_color": "#ff0055", "boss_hp": 1440,
        "ost": "niveau15.mp3", "patterns": ["flower", "pincer", "double_spiral"],
    },
    {
        "name": "Niveau 16 — L'Aube au-delà du Néant",
        "bg_top": "#160a02", "bg_bottom": "#5c2400",
        "trash_color": "#ffb347", "trash_hp": 7, "trash_count": 20, "trash_interval": 0.35,
        "boss_name": "Amaterasu Kagayaki, Porteuse de l'Aube Ultime", "boss_color": "#ffd60a", "boss_hp": 1650,
        "ost": "niveau16.mp3", "patterns": ["wall", "scatter", "double_spiral"],
    },
]


def _dist(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


class OstPlayer:
    """
    Lecteur de musique de fond, en boucle, basé sur QMediaPlayer. Si le fichier demandé
    n'existe pas dans assets/ost, le jeu reste simplement silencieux pour cette piste,
    plutôt que de planter ou d'afficher une erreur bloquante.
    """

    def __init__(self):
        self.audio_output = QAudioOutput()
        self.audio_output.setVolume(0.45)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.mediaStatusChanged.connect(self._on_status_changed)
        self.current_path = None

    def _on_status_changed(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.player.setPosition(0)
            self.player.play()

    def play_track(self, filename):
        path = os.path.join(OST_DIR, filename) if filename else None
        if path == self.current_path and self.player.playbackState() == QMediaPlayer.PlayingState:
            return  # déjà en train de jouer ce morceau, on ne relance pas depuis le début
        self.current_path = path
        if path and os.path.exists(path):
            self.player.setSource(QUrl.fromLocalFile(path))
            self.player.play()
        else:
            self.player.stop()

    def stop(self):
        self.player.stop()
        self.current_path = None

    def set_volume(self, value_0_to_1):
        self.audio_output.setVolume(max(0.0, min(1.0, value_0_to_1)))


def emit_radial(cx, cy, count, speed, color, angle_offset, out):
    for i in range(count):
        angle = angle_offset + (2 * math.pi * i / count)
        out.append(Bullet(cx, cy, math.cos(angle) * speed, math.sin(angle) * speed, 6, color))


def emit_aimed(cx, cy, px, py, speed, color, count, spread, out):
    base_angle = math.atan2(py - cy, px - cx)
    start = base_angle - spread * (count - 1) / 2
    for i in range(count):
        angle = start + spread * i
        out.append(Bullet(cx, cy, math.cos(angle) * speed, math.sin(angle) * speed, 6, color))


class Bullet:
    __slots__ = ("x", "y", "vx", "vy", "radius", "color")

    def __init__(self, x, y, vx, vy, radius, color):
        self.x, self.y, self.vx, self.vy, self.radius, self.color = x, y, vx, vy, radius, color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt

    def off_screen(self):
        return self.y < -30 or self.y > PLAY_H + 30 or self.x < -30 or self.x > PLAY_W + 30


# ---------------------------------------------------------------------------
# Pool de dix motifs de tir pour les boss. Chaque fonction a la même signature
# (boss, player, now, enemy_bullets, bonus) et se contente d'ajouter des Bullet
# à enemy_bullets ; certains motifs utilisent un peu d'état persistant stocké
# directement sur l'instance de Boss (spiral_angle, cross_angle, wave_t...).
# PATTERN_INTERVALS donne le rythme naturel de chaque motif : un mur ou une
# fleur se relance moins souvent qu'une spirale continue, par exemple. Le
# paramètre "bonus" reçu par chaque fonction inclut déjà le multiplicateur de
# difficulté (voir Boss.update).
# ---------------------------------------------------------------------------

def pattern_radial(boss, player, now, enemy_bullets, bonus):
    """Éventail circulaire classique, une salve régulière tout autour du boss."""
    emit_radial(boss.x, boss.y, 10 + boss.level_index, 95 + bonus, boss.color, now * 0.8, enemy_bullets)


def pattern_aimed(boss, player, now, enemy_bullets, bonus):
    """Petite rafale visée directement sur la position du joueur."""
    emit_aimed(boss.x, boss.y, player.x, player.y, 190 + bonus, boss.color, 3, 0.22, enemy_bullets)


def pattern_spiral(boss, player, now, enemy_bullets, bonus):
    """Spirale continue à trois bras qui tourne lentement autour du boss."""
    boss.spiral_angle += 0.26
    arms = 3
    for a in range(arms):
        angle = boss.spiral_angle + (2 * math.pi * a / arms)
        enemy_bullets.append(Bullet(boss.x, boss.y, math.cos(angle) * (95 + bonus), math.sin(angle) * (95 + bonus), 6, boss.color))


def pattern_double_spiral(boss, player, now, enemy_bullets, bonus):
    """Deux spirales à deux bras tournant en sens opposés, plus denses au centre."""
    boss.spiral_angle += 0.22
    for sign in (1, -1):
        for a in range(2):
            angle = boss.spiral_angle * sign + math.pi * a
            enemy_bullets.append(Bullet(boss.x, boss.y, math.cos(angle) * (90 + bonus), math.sin(angle) * (90 + bonus), 6, boss.color))


def pattern_wall(boss, player, now, enemy_bullets, bonus):
    """Mur de balles qui descend sur toute la largeur, avec un trou à traverser."""
    gap_x = PLAY_W / 2 + math.sin(now * 0.8) * (PLAY_W / 2 - 60)
    step = 24
    speed = 70 + bonus
    for x in range(10, PLAY_W - 10, step):
        if abs(x - gap_x) < step * 1.1:
            continue
        enemy_bullets.append(Bullet(x, boss.y + 20, 0, speed, 6, boss.color))


def pattern_cross(boss, player, now, enemy_bullets, bonus):
    """Croix à huit branches qui tourne lentement, plus large qu'une spirale classique."""
    boss.cross_angle += 0.16
    dirs = 8
    for i in range(dirs):
        angle = boss.cross_angle + (2 * math.pi * i / dirs)
        enemy_bullets.append(Bullet(boss.x, boss.y, math.cos(angle) * (100 + bonus), math.sin(angle) * (100 + bonus), 6, boss.color))


def pattern_wave(boss, player, now, enemy_bullets, bonus):
    """Flux de balles vers le bas qui ondule doucement de gauche à droite."""
    boss.wave_t += 0.3
    base_angle = math.pi / 2
    offset = math.sin(boss.wave_t) * 0.9
    for i in (-1, 0, 1):
        angle = base_angle + offset + i * 0.32
        enemy_bullets.append(Bullet(boss.x, boss.y, math.cos(angle) * (140 + bonus), math.sin(angle) * (140 + bonus), 6, boss.color))


def pattern_flower(boss, player, now, enemy_bullets, bonus):
    """Salves d'éventails successives légèrement décalées, formant une fleur/mandala."""
    boss.flower_step += 1
    emit_radial(boss.x, boss.y, 12, 100 + bonus, boss.color, boss.flower_step * 0.15, enemy_bullets)


def pattern_scatter(boss, player, now, enemy_bullets, bonus):
    """Tir dispersé et imprévisible dans un cône large autour de la direction du joueur."""
    base_angle = math.atan2(player.y - boss.y, player.x - boss.x)
    for _ in range(4):
        angle = base_angle + random.uniform(-0.7, 0.7)
        speed = random.uniform(120, 220) + bonus
        enemy_bullets.append(Bullet(boss.x, boss.y, math.cos(angle) * speed, math.sin(angle) * speed, 6, boss.color))


def pattern_pincer(boss, player, now, enemy_bullets, bonus):
    """Deux rafales symétriques qui convergent en tenaille de part et d'autre du joueur."""
    base_angle = math.atan2(player.y - boss.y, player.x - boss.x)
    for side in (-1, 1):
        for i in range(3):
            angle = base_angle + side * (0.5 + i * 0.12)
            enemy_bullets.append(Bullet(boss.x, boss.y, math.cos(angle) * (170 + bonus), math.sin(angle) * (170 + bonus), 6, boss.color))


PATTERN_FUNCS = {
    "radial": pattern_radial,
    "aimed": pattern_aimed,
    "spiral": pattern_spiral,
    "double_spiral": pattern_double_spiral,
    "wall": pattern_wall,
    "cross": pattern_cross,
    "wave": pattern_wave,
    "flower": pattern_flower,
    "scatter": pattern_scatter,
    "pincer": pattern_pincer,
}

PATTERN_INTERVALS = {
    "radial": 1.0,
    "aimed": 0.6,
    "spiral": 0.075,
    "double_spiral": 0.08,
    "wall": 1.5,
    "cross": 0.12,
    "wave": 0.1,
    "flower": 0.5,
    "scatter": 0.25,
    "pincer": 0.75,
}


class Player:
    def __init__(self, lives=STARTING_LIVES, bombs=STARTING_BOMBS):
        self.x = PLAY_W / 2
        self.y = PLAY_H - 60
        self.lives = lives
        self.bombs = bombs
        self.alive = True
        self.focus = False
        self.invincible_until = 0.0
        self.last_shot_at = 0.0

    def is_invincible(self, now):
        return now < self.invincible_until

    def hit(self, now):
        if self.is_invincible(now):
            return False
        self.lives -= 1
        self.invincible_until = now + INVINCIBLE_DURATION
        if self.lives <= 0:
            self.alive = False
        return True


class Trash:
    """Ennemi de vague, faible mais nombreux : abattu en quelques tirs, tire un shot visé."""

    def __init__(self, x, color, hp, speed):
        self.x = x
        self.y = -20.0
        self.color = color
        self.hp = hp
        self.max_hp = hp
        self.radius = 12
        self.speed = speed
        self.last_shot_at = 0.0
        self.phase = random.uniform(0, math.pi * 2)
        self.alive = True

    def update(self, dt, now, player, enemy_bullets):
        self.y += self.speed * dt
        self.x += math.sin(now * 2 + self.phase) * 22 * dt
        if now - self.last_shot_at > 1.6:
            self.last_shot_at = now
            emit_aimed(self.x, self.y, player.x, player.y, 160, self.color, 1, 0, enemy_bullets)

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.alive = False


class Boss:
    """
    Boss de fin de niveau : entre en scène, puis alterne entre trois motifs de tir qui
    lui sont propres (self.patterns), le motif changeant selon les PV restants plutôt
    que selon un minuteur. Ces trois motifs sont choisis niveau par niveau (voir
    LEVELS) parmi un pool de dix. bonus_mult vient du niveau de difficulté choisi sur
    l'écran titre et amplifie ou réduit la vitesse de tous ses tirs.
    """

    def __init__(self, name, color, max_hp, level_index, patterns, bonus_mult=1.0):
        self.name = name
        self.color = color
        self.max_hp = max_hp
        self.hp = max_hp
        self.x = PLAY_W / 2
        self.y = -60.0
        self.target_y = 110.0
        self.state = "entering"
        self.last_emit_at = 0.0
        self.level_index = level_index
        self.spawn_time = time.time()
        self.patterns = patterns  # [motif phase pleine vie, motif phase intermédiaire, motif phase critique]
        self.bonus_mult = bonus_mult

        # États internes utilisés par certains motifs (voir PATTERN_FUNCS ci-dessus)
        self.spiral_angle = 0.0
        self.cross_angle = 0.0
        self.wave_t = 0.0
        self.flower_step = 0

    def health_fraction(self):
        return max(0.0, self.hp / self.max_hp)

    def update(self, dt, now, player, enemy_bullets):
        if self.state == "entering":
            self.y += 90 * dt
            if self.y >= self.target_y:
                self.y = self.target_y
                self.state = "fighting"
                self.last_emit_at = now
            return

        if self.state != "fighting":
            return

        self.x = PLAY_W / 2 + math.sin(now * 0.7) * (PLAY_W / 2 - 50)
        frac = self.health_fraction()
        difficulty_bonus = self.level_index * 6 * self.bonus_mult

        if frac > 0.66:
            pattern_name = self.patterns[0]
        elif frac > 0.33:
            pattern_name = self.patterns[1]
        else:
            pattern_name = self.patterns[2]

        interval = PATTERN_INTERVALS[pattern_name]
        if now - self.last_emit_at >= interval:
            self.last_emit_at = now
            PATTERN_FUNCS[pattern_name](self, player, now, enemy_bullets, difficulty_bonus)

    def take_damage(self, amount):
        if self.state != "fighting":
            return
        self.hp = max(0, self.hp - amount)
        if self.hp <= 0:
            self.state = "defeated"


class BulletHell(QWidget):
    """Fenêtre de jeu, intégrable comme n'importe quelle autre application d'ALICEos."""

    def __init__(self, notifier=None):
        super().__init__()
        self.notifier = notifier
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(520, 480)
        self.setStyleSheet("background-color: #05050a;")

        _ensure_ost_dir()

        self.pressed_keys = set()
        self.last_time = time.time()
        self.difficulty_index = DEFAULT_DIFFICULTY_INDEX
        self.stars = [
            [random.uniform(0, PLAY_W), random.uniform(0, PLAY_H), random.uniform(30, 90), random.uniform(1, 2.4)]
            for _ in range(50)
        ]

        self.ost = OstPlayer()

        # begin=False : au premier lancement, on s'arrête à l'écran titre plutôt que
        # de démarrer le niveau 1 directement.
        self._start_new_game(begin=False)
        self.ost.play_track(TITLE_OST)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(16)

    # --- Difficulté ---

    def _current_difficulty(self):
        return DIFFICULTIES[self.difficulty_index]

    def _change_difficulty(self, delta):
        self.difficulty_index = max(0, min(len(DIFFICULTIES) - 1, self.difficulty_index + delta))

    # --- Cycle de vie de la partie ---

    def _start_new_game(self, begin=True):
        diff = self._current_difficulty()
        self.level_index = 0
        self.score = 0
        self.player = Player(
            lives=max(1, STARTING_LIVES + diff["lives"]),
            bombs=max(0, STARTING_BOMBS + diff["bombs"]),
        )
        self.player_bullets = []
        self.enemy_bullets = []
        self.trash_enemies = []
        self.boss = None
        self.trash_spawned = 0
        self.game_over = False
        self.victory = False
        now = time.time()
        if begin:
            self._enter_level_intro(now)
        else:
            self._enter_state("title", now)

    def _continue_from_save(self):
        save = self._load_save()
        if not save:
            return
        self.difficulty_index = max(0, min(len(DIFFICULTIES) - 1, int(save.get("difficulty_index", DEFAULT_DIFFICULTY_INDEX))))
        self._start_new_game(begin=False)
        self.level_index = max(0, min(len(LEVELS) - 1, int(save.get("level_index", 0))))
        self.score = int(save.get("score", 0))
        self._enter_level_intro(time.time())
        if self.notifier:
            self.notifier.notify("Bullet Hell", f"Sauvegarde chargée : niveau {self.level_index + 1}.")

    def _current_level(self):
        return LEVELS[self.level_index]

    def _enter_state(self, new_state, now):
        self.state = new_state
        self.state_entered_at = now

    def _enter_level_intro(self, now):
        self._enter_state("level_intro", now)
        self.trash_spawned = 0
        self._last_trash_spawn = 0.0
        self.ost.play_track(self._current_level()["ost"])

    # --- Sauvegarde ---

    def _save_game(self):
        data = {"level_index": self.level_index, "score": self.score, "difficulty_index": self.difficulty_index}
        try:
            os.makedirs(os.path.dirname(SAVE_PATH), exist_ok=True)
            with open(SAVE_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f)
            if self.notifier:
                self.notifier.notify("Bullet Hell", "Partie sauvegardée.")
        except OSError:
            if self.notifier:
                self.notifier.notify("Bullet Hell", "Impossible d'enregistrer la sauvegarde.")

    def _has_save(self):
        return os.path.exists(SAVE_PATH)

    def _load_save(self):
        try:
            with open(SAVE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    # --- Entrées clavier ---

    def keyPressEvent(self, event):
        self.pressed_keys.add(event.key())
        key = event.key()

        if event.key() in (Qt.Key_Shift,):
            self.player.focus = True

        if self.state == "title":
            if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Z, Qt.Key_Space):
                self._start_new_game(begin=True)
            elif key == Qt.Key_C and self._has_save():
                self._continue_from_save()
            elif key in (Qt.Key_Left, Qt.Key_A):
                self._change_difficulty(-1)
            elif key in (Qt.Key_Right, Qt.Key_D):
                self._change_difficulty(1)
            return

        if self.state == "level_menu":
            if key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Z, Qt.Key_Space):
                self._advance_to_next_level()
            elif key == Qt.Key_S:
                self._save_game()
            elif key == Qt.Key_M:
                self._enter_state("title", time.time())
                self.ost.play_track(TITLE_OST)
            return

        if key == Qt.Key_X:
            self._use_bomb()
        if key == Qt.Key_M and (self.game_over or self.victory):
            self._enter_state("title", time.time())
            self.ost.play_track(TITLE_OST)
        if key == Qt.Key_R and (self.game_over or self.victory):
            self._start_new_game(begin=True)
            self.ost.play_track(self._current_level()["ost"])

    def keyReleaseEvent(self, event):
        self.pressed_keys.discard(event.key())
        if event.key() == Qt.Key_Shift:
            self.player.focus = False

    def mousePressEvent(self, event):
        self.setFocus()

    def _use_bomb(self):
        if self.game_over or self.victory or self.player.bombs <= 0 or not self.player.alive:
            return
        self.player.bombs -= 1
        self.enemy_bullets.clear()
        self.player.invincible_until = time.time() + 1.2
        if self.notifier:
            self.notifier.notify("Bullet Hell", "Bombe utilisée : l'écran est nettoyé.")

    def _advance_to_next_level(self):
        diff = self._current_difficulty()
        if self.level_index + 1 >= len(LEVELS):
            self.victory = True
            self.ost.stop()
        else:
            self.level_index += 1
            self.player.bombs = max(0, STARTING_BOMBS + diff["bombs"])
            self.boss = None
            self._enter_level_intro(time.time())

    # --- Boucle de jeu ---

    def _tick(self):
        now = time.time()
        dt = min(0.05, now - self.last_time)
        self.last_time = now

        if self.state in ("title", "level_menu"):
            self.update()
            return

        if not self.game_over and not self.victory:
            self._update_state_machine(dt, now)
            self._update_player(dt, now)
            self._update_bullets(dt)
            self._update_enemies(dt, now)
            self._handle_collisions(now)

        self.update()

    def _update_player(self, dt, now):
        p = self.player
        if not p.alive:
            return
        keys = self.pressed_keys
        speed = PLAYER_SPEED_FOCUS if p.focus else PLAYER_SPEED_NORMAL

        dx = (1 if Qt.Key_Right in keys or Qt.Key_D in keys else 0) - (1 if Qt.Key_Left in keys or Qt.Key_A in keys else 0)
        dy = (1 if Qt.Key_Down in keys or Qt.Key_S in keys else 0) - (1 if Qt.Key_Up in keys or Qt.Key_W in keys else 0)
        if dx or dy:
            length = math.hypot(dx, dy) or 1
            p.x = max(PLAYER_SPRITE_RADIUS, min(PLAY_W - PLAYER_SPRITE_RADIUS, p.x + dx / length * speed * dt))
            p.y = max(PLAYER_SPRITE_RADIUS, min(PLAY_H - PLAYER_SPRITE_RADIUS, p.y + dy / length * speed * dt))

        shooting = Qt.Key_Z in keys or Qt.Key_Space in keys
        if shooting and now - p.last_shot_at >= PLAYER_FIRE_INTERVAL:
            p.last_shot_at = now
            self.player_bullets.append(Bullet(p.x - 6, p.y, 0, -PLAYER_BULLET_SPEED, 4, "#bfffff"))
            self.player_bullets.append(Bullet(p.x + 6, p.y, 0, -PLAYER_BULLET_SPEED, 4, "#bfffff"))

    def _update_bullets(self, dt):
        for b in self.player_bullets:
            b.update(dt)
        for b in self.enemy_bullets:
            b.update(dt)
        self.player_bullets = [b for b in self.player_bullets if not b.off_screen()]
        self.enemy_bullets = [b for b in self.enemy_bullets if not b.off_screen()]

    def _update_enemies(self, dt, now):
        for e in self.trash_enemies:
            e.update(dt, now, self.player, self.enemy_bullets)
        self.trash_enemies = [e for e in self.trash_enemies if e.alive and e.y < PLAY_H + 40]
        if self.boss is not None:
            self.boss.update(dt, now, self.player, self.enemy_bullets)

    def _handle_collisions(self, now):
        for e in self.trash_enemies:
            if not e.alive:
                continue
            for b in self.player_bullets:
                if b.radius <= 0:
                    continue
                if _dist(b.x, b.y, e.x, e.y) <= b.radius + e.radius:
                    e.take_damage(PLAYER_BULLET_DAMAGE)
                    b.radius = -1
                    if not e.alive:
                        self.score += 100
                    break

        if self.boss is not None and self.boss.state == "fighting":
            for b in self.player_bullets:
                if b.radius <= 0:
                    continue
                if _dist(b.x, b.y, self.boss.x, self.boss.y) <= b.radius + 26:
                    self.boss.take_damage(PLAYER_BULLET_DAMAGE)
                    b.radius = -1

        self.player_bullets = [b for b in self.player_bullets if b.radius > 0]

        p = self.player
        if p.alive and not p.is_invincible(now):
            for b in self.enemy_bullets:
                if _dist(b.x, b.y, p.x, p.y) <= b.radius + PLAYER_HIT_RADIUS:
                    if p.hit(now):
                        if self.notifier and not p.alive:
                            self.notifier.notify("Bullet Hell", "Vaisseau détruit.")
                    break

    # --- Machine à états de la progression ---

    def _update_state_machine(self, dt, now):
        level = self._current_level()
        diff = self._current_difficulty()
        elapsed = now - self.state_entered_at

        if self.state == "level_intro":
            if elapsed > 1.6:
                self._enter_state("wave", now)

        elif self.state == "wave":
            if self.trash_spawned < level["trash_count"] and elapsed - getattr(self, "_last_trash_spawn", 0) >= level["trash_interval"]:
                self._last_trash_spawn = elapsed
                self.trash_spawned += 1
                x = random.uniform(40, PLAY_W - 40)
                speed = (50 + self.level_index * 5) * diff["trash_speed_mult"]
                hp = max(1, round(level["trash_hp"] * diff["trash_hp_mult"]))
                self.trash_enemies.append(Trash(x, level["trash_color"], hp, speed))
            if self.trash_spawned >= level["trash_count"] and not self.trash_enemies:
                self._enter_state("boss_intro", now)

        elif self.state == "boss_intro":
            if elapsed > 1.6:
                boss_hp = max(1, round(level["boss_hp"] * diff["hp_mult"]))
                self.boss = Boss(level["boss_name"], level["boss_color"], boss_hp, self.level_index,
                                  level["patterns"], bonus_mult=diff["bonus_mult"])
                self._enter_state("boss", now)

        elif self.state == "boss":
            if self.boss and self.boss.state == "defeated":
                self.score += 1000
                self.enemy_bullets.clear()
                self._enter_state("level_clear", now)

        elif self.state == "level_clear":
            if elapsed > 1.2:
                self._enter_state("level_menu", now)
                self.ost.play_track(TITLE_OST)

        if not self.player.alive:
            self.game_over = True
            self.ost.stop()

    # --- Rendu ---

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()

        available_w = max(50, w - HUD_W)
        scale = min(available_w / PLAY_W, h / PLAY_H)
        arena_w, arena_h = PLAY_W * scale, PLAY_H * scale
        arena_x = (available_w - arena_w) / 2
        arena_y = (h - arena_h) / 2

        painter.fillRect(QRectF(0, 0, w, h), QColor("#050508"))

        painter.save()
        painter.translate(arena_x, arena_y)
        painter.scale(scale, scale)
        painter.setClipRect(QRectF(0, 0, PLAY_W, PLAY_H))

        if self.state == "title":
            self._draw_background(painter, TITLE_BG_TOP, TITLE_BG_BOTTOM)
        elif self.state == "level_menu":
            lvl = self._current_level()
            self._draw_background(painter, lvl["bg_top"], lvl["bg_bottom"])
        else:
            lvl = self._current_level()
            self._draw_background(painter, lvl["bg_top"], lvl["bg_bottom"])
            self._draw_gameplay_entities(painter)

        painter.restore()

        painter.setPen(QPen(QColor("#2a2a38"), 2))
        painter.drawRect(QRectF(arena_x, arena_y, arena_w, arena_h))

        if self.state != "title":
            self._draw_hud(painter, arena_x + arena_w + 12, arena_y, HUD_W - 20, arena_h)

        if self.state == "title":
            self._draw_title_screen(painter, arena_x, arena_y, arena_w, arena_h)
        elif self.state == "level_menu":
            self._draw_level_menu_screen(painter, arena_x, arena_y, arena_w, arena_h)
        elif self.game_over:
            self._draw_banner(painter, arena_x, arena_y, arena_w, arena_h, "VAISSEAU DÉTRUIT", "R : recommencer   —   M : menu titre", "#ff4d4d")
        elif self.victory:
            self._draw_banner(painter, arena_x, arena_y, arena_w, arena_h, "SANCTUAIRE LIBÉRÉ", f"Score final : {self.score}   —   R : rejouer   —   M : menu titre", "#4dffb3")
        elif self.state == "level_intro":
            self._draw_banner(painter, arena_x, arena_y, arena_w, arena_h, self._current_level()["name"], "", "#ffffff")
        elif self.state == "boss_intro":
            self._draw_banner(painter, arena_x, arena_y, arena_w, arena_h, self._current_level()["boss_name"], "Prépare-toi !", self._current_level()["boss_color"])
        elif self.state == "level_clear":
            self._draw_banner(painter, arena_x, arena_y, arena_w, arena_h, "NIVEAU NETTOYÉ", "", "#4dffb3")

        painter.end()

    def _draw_background(self, painter, top_hex, bottom_hex):
        gradient_top = QColor(top_hex)
        gradient_bottom = QColor(bottom_hex)
        for i in range(0, int(PLAY_H), 4):
            t = i / PLAY_H
            r = gradient_top.red() + (gradient_bottom.red() - gradient_top.red()) * t
            g = gradient_top.green() + (gradient_bottom.green() - gradient_top.green()) * t
            b = gradient_top.blue() + (gradient_bottom.blue() - gradient_top.blue()) * t
            painter.fillRect(QRectF(0, i, PLAY_W, 4), QColor(int(r), int(g), int(b)))

        painter.setBrush(QBrush(QColor(255, 255, 255, 160)))
        painter.setPen(Qt.NoPen)
        for star in self.stars:
            star[1] += star[2] * 0.016
            if star[1] > PLAY_H:
                star[1] = 0
                star[0] = random.uniform(0, PLAY_W)
            painter.drawEllipse(QPointF(star[0], star[1]), star[3], star[3])

    def _draw_gameplay_entities(self, painter):
        now = time.time()

        for e in self.trash_enemies:
            painter.setBrush(QBrush(QColor(e.color)))
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawEllipse(QPointF(e.x, e.y), e.radius, e.radius)

        if self.boss is not None and self.boss.state != "defeated":
            b = self.boss
            painter.setBrush(QBrush(QColor(b.color)))
            painter.setPen(QPen(QColor("#ffffff"), 2))
            painter.drawEllipse(QPointF(b.x, b.y), 30, 30)
            painter.setBrush(QBrush(QColor(b.color).lighter(140)))
            painter.drawEllipse(QPointF(b.x, b.y), 14, 14)

        for bullet in self.enemy_bullets:
            painter.setBrush(QBrush(QColor(bullet.color)))
            painter.setPen(QPen(QColor("#ffffff"), 1))
            painter.drawEllipse(QPointF(bullet.x, bullet.y), bullet.radius, bullet.radius)

        for bullet in self.player_bullets:
            painter.setBrush(QBrush(QColor(bullet.color)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(bullet.x, bullet.y), bullet.radius, bullet.radius)

        p = self.player
        if p.alive:
            blinking = p.is_invincible(now) and int(now * 12) % 2 == 0
            if not blinking:
                painter.setBrush(QBrush(QColor("#7fd7ff")))
                painter.setPen(QPen(QColor("#ffffff"), 1.5))
                painter.drawEllipse(QPointF(p.x, p.y), PLAYER_SPRITE_RADIUS, PLAYER_SPRITE_RADIUS)
                if p.focus:
                    painter.setBrush(QBrush(QColor("#ff3b3b")))
                    painter.setPen(Qt.NoPen)
                    painter.drawEllipse(QPointF(p.x, p.y), PLAYER_HIT_RADIUS, PLAYER_HIT_RADIUS)

        if self.boss is not None and self.boss.state == "fighting":
            frac = self.boss.health_fraction()
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#2a2a38")))
            painter.drawRect(QRectF(20, 16, PLAY_W - 40, 10))
            painter.setBrush(QBrush(QColor(self.boss.color)))
            painter.drawRect(QRectF(20, 16, (PLAY_W - 40) * frac, 10))

    def _draw_hud(self, painter, x, y, width, height):
        painter.setFont(QFont("Consolas", 11, QFont.Bold))
        painter.setPen(QColor("#f2f2f7"))
        lines = [
            f"Niveau {self.level_index + 1} / {len(LEVELS)}",
            f"Difficulté : {self._current_difficulty()['label']}",
            f"Score : {self.score}",
            f"Vies : ♥ x {self.player.lives}",
            f"Bombes : {'● ' * max(0, self.player.bombs)}".strip() or "Bombes : —",
        ]
        for i, line in enumerate(lines):
            painter.drawText(QRectF(x, y + i * 24, width, 22), Qt.AlignLeft | Qt.AlignVCenter, line)

        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QColor("#9a9ab0"))
        help_lines = [
            "Flèches/ZQSD : bouger",
            "Z ou Espace : tirer",
            "Maj : concentration",
            "(hitbox réduite visible)",
            "X : bombe",
            "M : retour au titre",
        ]
        for i, line in enumerate(help_lines):
            painter.drawText(QRectF(x, y + height - len(help_lines) * 18 + i * 18, width, 18), Qt.AlignLeft, line)

    def _draw_banner(self, painter, ax, ay, aw, ah, title, subtitle, color_hex):
        painter.fillRect(QRectF(ax, ay, aw, ah), QColor(0, 0, 0, 150))
        painter.setFont(QFont("Consolas", 18, QFont.Bold))
        painter.setPen(QColor(color_hex))
        painter.drawText(QRectF(ax, ay + ah / 2 - 30, aw, 40), Qt.AlignCenter, title)
        if subtitle:
            painter.setFont(QFont("Consolas", 11))
            painter.setPen(QColor("#dddddd"))
            painter.drawText(QRectF(ax, ay + ah / 2 + 12, aw, 30), Qt.AlignCenter, subtitle)

    def _draw_title_screen(self, painter, ax, ay, aw, ah):
        painter.fillRect(QRectF(ax, ay, aw, ah), QColor(0, 0, 0, 120))

        painter.setFont(QFont("Consolas", 26, QFont.Bold))
        painter.setPen(QColor("#e07dff"))
        painter.drawText(QRectF(ax, ay + ah * 0.18, aw, 50), Qt.AlignCenter, "BULLET HELL")

        painter.setFont(QFont("Consolas", 11))
        painter.setPen(QColor("#c7c7d6"))
        painter.drawText(QRectF(ax, ay + ah * 0.18 + 46, aw, 26), Qt.AlignCenter, "un shoot 'em up façon danmaku — ALICEos")

        blink_on = int(time.time() * 1.6) % 2 == 0
        painter.setFont(QFont("Consolas", 13, QFont.Bold))
        painter.setPen(QColor("#ffffff") if blink_on else QColor("#88889a"))
        painter.drawText(QRectF(ax, ay + ah * 0.46, aw, 26), Qt.AlignCenter, "Entrée : Nouvelle partie")

        painter.setFont(QFont("Consolas", 11))
        if self._has_save():
            painter.setPen(QColor("#8ec6ff"))
            painter.drawText(QRectF(ax, ay + ah * 0.46 + 30, aw, 24), Qt.AlignCenter, "C : Continuer la sauvegarde")
        else:
            painter.setPen(QColor("#66667a"))
            painter.drawText(QRectF(ax, ay + ah * 0.46 + 30, aw, 24), Qt.AlignCenter, "(aucune sauvegarde pour l'instant)")

        diff = self._current_difficulty()
        painter.setFont(QFont("Consolas", 13, QFont.Bold))
        painter.setPen(QColor("#ffd60a"))
        painter.drawText(QRectF(ax, ay + ah * 0.46 + 66, aw, 28), Qt.AlignCenter, f"◀  Difficulté : {diff['label']}  ▶")
        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QColor("#9a9ab0"))
        painter.drawText(QRectF(ax, ay + ah * 0.46 + 94, aw, 20), Qt.AlignCenter, "Flèches gauche/droite pour changer")

        painter.setFont(QFont("Consolas", 9))
        painter.setPen(QColor("#9a9ab0"))
        controls = [
            "Flèches/ZQSD : bouger      Z/Espace : tirer",
            "Maj : concentration (hitbox visible)      X : bombe",
        ]
        for i, line in enumerate(controls):
            painter.drawText(QRectF(ax, ay + ah - 60 + i * 20, aw, 20), Qt.AlignCenter, line)

    def _draw_level_menu_screen(self, painter, ax, ay, aw, ah):
        painter.fillRect(QRectF(ax, ay, aw, ah), QColor(0, 0, 0, 150))

        level = self._current_level()
        painter.setFont(QFont("Consolas", 16, QFont.Bold))
        painter.setPen(QColor("#4dffb3"))
        title = "TOUS LES NIVEAUX SONT TERMINÉS" if self.level_index + 1 >= len(LEVELS) else f"NIVEAU {self.level_index + 1} TERMINÉ"
        painter.drawText(QRectF(ax, ay + ah * 0.28, aw, 34), Qt.AlignCenter, title)

        painter.setFont(QFont("Consolas", 11))
        painter.setPen(QColor("#dddddd"))
        painter.drawText(QRectF(ax, ay + ah * 0.28 + 36, aw, 24), Qt.AlignCenter, f"Score actuel : {self.score}")

        options = [
            ("Entrée", "Niveau suivant" if self.level_index + 1 < len(LEVELS) else "Voir la victoire"),
            ("S", "Sauvegarder la partie"),
            ("M", "Retour au menu titre"),
        ]
        painter.setFont(QFont("Consolas", 12))
        for i, (key, label) in enumerate(options):
            y = ay + ah * 0.52 + i * 28
            painter.setPen(QColor("#ffffff"))
            painter.drawText(QRectF(ax, y, aw, 24), Qt.AlignCenter, f"{key} : {label}")
