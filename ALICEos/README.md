# ALICEos

Un système d'exploitation virtuel de bureau, entièrement simulé, développé en Python avec PySide6 (Qt pour Python). ALICEos se lance dans une seule fenêtre plein écran et reproduit l'expérience d'un vrai bureau, sans jamais toucher au système réel.

## Lancement depuis Visual Studio Code

1. Ouvre le dossier `ALICEos/` dans VS Code.
2. Ouvre un terminal intégré (`Ctrl + ù` ou `Terminal > Nouveau terminal`).
3. Installe la dépendance unique du projet.

   ```bash
   pip install -r requirements.txt
   ```

4. Lance le système.

   ```bash
   python main.py
   ```

L'application s'ouvre automatiquement en plein écran, affiche l'écran de démarrage, puis l'écran de connexion. Le mot de passe par défaut est `alice`, il peut être changé depuis Paramètres > Compte.

Pour quitter, ferme la fenêtre normalement (Alt+F4 sous Linux/Windows, ou combinaison équivalente), ALICEos ne verrouille pas le système hôte.

## Architecture du projet

```
ALICEos/
├── main.py                  point d'entrée, orchestre boot / connexion / bureau
├── requirements.txt
├── system/
│   ├── settings_manager.py  paramètres persistés en JSON (thème, utilisateur, mot de passe)
│   ├── virtual_fs.py        système de fichiers virtuel (dossiers, fichiers, corbeille)
│   ├── window_manager.py    ouverture, suivi et animation des fenêtres internes
│   └── themes.py            palettes et feuilles de style clair / sombre
├── ui/
│   ├── boot_screen.py       écran de démarrage animé
│   ├── lock_screen.py       écran de connexion et de verrouillage
│   ├── desktop.py           fond d'écran, icônes, zone des fenêtres, menu contextuel
│   ├── taskbar.py           barre des tâches, menu Démarrer, horloge
│   └── notifications.py     notifications toast
├── apps/
│   ├── file_explorer.py     explorateur de fichiers virtuel
│   ├── terminal.py          terminal avec jeu de commandes shell simulées
│   ├── calculator.py        calculatrice
│   ├── browser.py           navigateur web simulé (pages internes fictives)
│   ├── notepad.py           bloc-notes relié au système de fichiers virtuel
│   ├── settings_app.py      paramètres système (thème, fond d'écran, compte)
│   └── task_manager.py      gestionnaire de tâches
└── assets/                  emplacement prévu pour icônes, fonds d'écran, sons personnalisés
```

## Fonctionnalités incluses

- Démarrage plein écran avec écran de boot animé (logo, barre de progression, texte d'état).
- Bureau avec fond d'écran en dégradé (plusieurs choix), icônes, barre des tâches, horloge, zone de notifications.
- Gestion de fenêtres complète via `QMdiArea` : déplacement, redimensionnement, réduction, agrandissement, fermeture, avec animation de fondu à l'ouverture.
- Explorateur de fichiers simulé, avec création, renommage, suppression vers la corbeille, navigation par raccourcis.
- Terminal intégré (`ls`, `cd`, `cat`, `mkdir`, `touch`, `rm`, `echo`, `whoami`, `date`, `pwd`, `help`, `clear`).
- Calculatrice, bloc-notes, navigateur web simulé.
- Paramètres système avec thèmes clair / sombre, choix du fond d'écran, gestion du compte et du mot de passe.
- Gestion des utilisateurs avec écran de connexion et écran de verrouillage de session.
- Menu contextuel (clic droit sur le bureau et dans l'explorateur).
- Notifications système sous forme de toasts animés.
- Gestionnaire de tâches listant les fenêtres ouvertes.
- Système de fichiers virtuel et paramètres persistés dans `~/.aliceos/` au format JSON, donc conservés d'une session à l'autre.

## Extensions possibles

Le projet est organisé pour être facilement étendu. Pour ajouter une nouvelle application, il suffit de créer un module dans `apps/`, puis de l'enregistrer dans la liste `APPS` de `ui/taskbar.py` et dans la méthode `open_app` de `main.py`. Des pistes pour aller plus loin, non incluses dans cette version afin de garder une base saine et testée : sons de démarrage et d'arrêt, magasin d'applications fictif, système de mise à jour simulé, animations de fermeture de fenêtre plus élaborées.
