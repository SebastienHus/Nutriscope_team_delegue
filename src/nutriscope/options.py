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
from dotenv import load_dotenv

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


# ============================================================================
# CONNEXION POSTGRESQL
# ============================================================================
# Mêmes variables que le conteneur `db` (compose.yml) : POSTGRES_USER vient du `.env`,
# le mot de passe du secret Docker `secrets/db_password.txt` (scripts/init-secrets.*).
ENV_FILE = ROOT_PATH / ".env"
DB_USER_ENV = "POSTGRES_USER"
DB_PASSWORD_ENV = "POSTGRES_PASSWORD"
DB_PASSWORD_FILE_ENV = "POSTGRES_PASSWORD_FILE"
DB_HOST_ENV = "POSTGRES_HOST"
DB_PORT_ENV = "POSTGRES_PORT"
DEFAULT_DB_PASSWORD_FILE = ROOT_PATH / "secrets" / "db_password.txt"


def load_env_file(path: os.PathLike = ENV_FILE) -> None:
    """Charge les `CLE=valeur` du `.env` sans écraser une variable déjà définie dans le shell."""
    load_dotenv(path, override=False, encoding="utf-8")


def db_credentials(password_file: os.PathLike = DEFAULT_DB_PASSWORD_FILE) -> dict | None:
    """
    Identifiants PostgreSQL pour `create_database.init_database`, ou `None` sans mot de passe.

    Mot de passe : POSTGRES_PASSWORD, sinon le fichier POSTGRES_PASSWORD_FILE, sinon
    `secrets/db_password.txt`. Utilisateur, hôte, port : POSTGRES_USER / _HOST / _PORT.
    """
    load_env_file()
    password = os.environ.get(DB_PASSWORD_ENV)
    if not password:
        path = Path(os.environ.get(DB_PASSWORD_FILE_ENV) or password_file)
        if path.is_file():
            password = path.read_text(encoding="utf-8").strip()
    if not password:
        return None
    return {
        "username": os.environ.get(DB_USER_ENV, "postgres"),
        "password": password,
        "host": os.environ.get(DB_HOST_ENV, "localhost"),
        "port": int(os.environ.get(DB_PORT_ENV, "5432")),
    }

# Graine et part de test du split figé (TP 13), réutilisées par la phase 4
RANDOM_SEED = int(CONFIG["training"]["seed"])
TEST_SIZE = float(CONFIG["training"]["test_size"])
