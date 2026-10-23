"""
Options partagées du package : chemins du dépôt, configuration et graine.

Tous les chemins sont résolus à partir de l'emplacement de ce fichier, jamais à partir
du dossier courant : le package fonctionne quel que soit le dossier de lancement
(racine du dépôt, `notebooks/`, `tests/`). Il suppose une installation éditable
(`pip install -e .`), qui laisse le code dans le dépôt.
"""

import configparser
import os
from pathlib import Path

PACKAGE_PATH = Path(__file__).resolve().parent
ROOT_PATH = PACKAGE_PATH.parents[1]                  # src/nutriscope/ → racine du dépôt
DATA_PATH = ROOT_PATH / "data"                       # sorties du pipeline (hors Git)
SHARED_DATA_PATH = ROOT_PATH / "data-nutriscope"     # jeu partagé (échantillon, jeux ML)
CONFIG_PATH = PACKAGE_PATH / "options.ini"


def read_options(filename: os.PathLike) -> dict:
    """Lit le fichier d'options : sections en dictionnaires, `columns` en liste."""
    config_obj = configparser.ConfigParser(allow_no_value=True)  # requis pour les listes sans valeur
    config_obj.read(filename, encoding="utf-8")

    config = {section: dict(config_obj.items(section)) for section in config_obj.sections()}
    config["columns"] = list(config["columns"])
    config["database"]["categories"] = [
        category.strip() for category in config["database"]["categories"].split(",")
    ]
    return config


CONFIG = read_options(CONFIG_PATH)

# Graine et part de test du split figé (TP 13), réutilisées par la phase 4
RANDOM_SEED = int(CONFIG["training"]["seed"])
TEST_SIZE = float(CONFIG["training"]["test_size"])
