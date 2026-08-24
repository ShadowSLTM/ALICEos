"""
Système de fichiers virtuel pour ALICEos.
Toute l'arborescence (dossiers, fichiers texte, corbeille) est représentée en mémoire
sous forme de dictionnaires imbriqués, puis persistée dans virtual_fs.json.
Cela permet à l'explorateur de fichiers, au terminal et au bloc-notes de partager
la même vision cohérente du "disque" sans jamais toucher au vrai système de fichiers.
"""

import json
import os
import time


class VNode:
    """Représente un noeud du système de fichiers virtuel (dossier ou fichier)."""

    def __init__(self, name, is_dir=True, content="", children=None):
        self.name = name
        self.is_dir = is_dir
        self.content = content
        self.children = children if children is not None else {}
        self.modified = time.time()

    def to_dict(self):
        return {
            "name": self.name,
            "is_dir": self.is_dir,
            "content": self.content,
            "modified": self.modified,
            "children": {k: v.to_dict() for k, v in self.children.items()} if self.is_dir else {},
        }

    @staticmethod
    def from_dict(data):
        node = VNode(data["name"], data.get("is_dir", True), data.get("content", ""))
        node.modified = data.get("modified", time.time())
        if node.is_dir:
            node.children = {k: VNode.from_dict(v) for k, v in data.get("children", {}).items()}
        return node


class VirtualFileSystem:
    """Arborescence de fichiers simulée, avec racine, dossiers standards et corbeille."""

    def __init__(self, base_dir):
        self.path = os.path.join(base_dir, "virtual_fs.json")
        self.root = None
        self.load()

    def _default_tree(self):
        root = VNode("Ce PC", is_dir=True)
        bureau = VNode("Bureau", is_dir=True)
        docs = VNode("Documents", is_dir=True)
        images = VNode("Images", is_dir=True)
        telechargements = VNode("Téléchargements", is_dir=True)
        corbeille = VNode("Corbeille", is_dir=True)

        readme = VNode("Bienvenue.txt", is_dir=False,
                        content="Bienvenue sur ALICEos !\n\nCeci est ton nouveau bureau virtuel.\n"
                                "Explore les applications, crée des fichiers, personnalise ton thème.")
        docs.children["Bienvenue.txt"] = readme

        root.children = {
            "Bureau": bureau,
            "Documents": docs,
            "Images": images,
            "Téléchargements": telechargements,
            "Corbeille": corbeille,
        }
        return root

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.root = VNode.from_dict(data)
                return
            except (json.JSONDecodeError, OSError):
                pass
        self.root = self._default_tree()
        self.save()

    def save(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.root.to_dict(), f, indent=2, ensure_ascii=False)

    def resolve(self, path_parts):
        """Retourne le VNode correspondant à une liste de segments de chemin, ou None."""
        node = self.root
        for part in path_parts:
            if not node.is_dir or part not in node.children:
                return None
            node = node.children[part]
        return node

    def list_dir(self, path_parts):
        node = self.resolve(path_parts)
        if node is None or not node.is_dir:
            return []
        return sorted(node.children.values(), key=lambda n: (not n.is_dir, n.name.lower()))

    def create_folder(self, path_parts, name):
        parent = self.resolve(path_parts)
        if parent and parent.is_dir and name not in parent.children:
            parent.children[name] = VNode(name, is_dir=True)
            self.save()
            return True
        return False

    def create_file(self, path_parts, name, content=""):
        parent = self.resolve(path_parts)
        if parent and parent.is_dir and name not in parent.children:
            parent.children[name] = VNode(name, is_dir=False, content=content)
            self.save()
            return True
        return False

    def write_file(self, path_parts, name, content):
        parent = self.resolve(path_parts)
        if parent and parent.is_dir and name in parent.children:
            parent.children[name].content = content
            parent.children[name].modified = time.time()
            self.save()
            return True
        return False

    def delete_to_trash(self, path_parts, name):
        """Déplace un élément vers la corbeille plutôt que de le supprimer définitivement."""
        parent = self.resolve(path_parts)
        trash = self.resolve(["Corbeille"])
        if parent and trash and name in parent.children:
            node = parent.children.pop(name)
            # Évite les collisions de noms dans la corbeille
            trash_name = node.name
            counter = 1
            while trash_name in trash.children:
                trash_name = f"{node.name} ({counter})"
                counter += 1
            node.name = trash_name
            trash.children[trash_name] = node
            self.save()
            return True
        return False

    def delete_permanently(self, path_parts, name):
        parent = self.resolve(path_parts)
        if parent and name in parent.children:
            del parent.children[name]
            self.save()
            return True
        return False

    def rename(self, path_parts, old_name, new_name):
        parent = self.resolve(path_parts)
        if parent and old_name in parent.children and new_name not in parent.children:
            node = parent.children.pop(old_name)
            node.name = new_name
            parent.children[new_name] = node
            self.save()
            return True
        return False
