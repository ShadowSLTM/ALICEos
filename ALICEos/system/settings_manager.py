"""
Gestionnaire de paramètres système pour ALICEos.
Persiste les préférences (thème, fond d'écran, utilisateur, mot de passe) dans un fichier JSON,
de façon à ce que l'état de la session soit conservé d'un lancement à l'autre.
"""

import json
import os
import hashlib


DEFAULT_SETTINGS = {
    "theme": "dark",
    "wallpaper": "gradient_purple",
    "username": "Seydou",
    "password_hash": hashlib.sha256("alice".encode()).hexdigest(),
    "volume": 70,
    "boot_animation": True,
    "language": "fr",
}


class SettingsManager:
    """Charge, modifie et sauvegarde les paramètres du système dans settings.json."""

    def __init__(self, base_dir):
        self.path = os.path.join(base_dir, "settings.json")
        self.settings = dict(DEFAULT_SETTINGS)
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self.settings.update(saved)
            except (json.JSONDecodeError, OSError):
                # En cas de fichier corrompu, on retombe sur les valeurs par défaut
                self.settings = dict(DEFAULT_SETTINGS)
        else:
            self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)

    def get(self, key, default=None):
        return self.settings.get(key, default)

    def set(self, key, value):
        self.settings[key] = value
        self.save()

    def check_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest() == self.settings.get("password_hash")

    def set_password(self, password):
        self.set("password_hash", hashlib.sha256(password.encode()).hexdigest())
