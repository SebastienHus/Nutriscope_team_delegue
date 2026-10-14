"""
Étape 3 — `charger_base` : nettoyé → base PostgreSQL (rechargement complet) + `data/db/base_<AAAAMMJJ>.json`.

- Réutilise `create_database.init_database` (rejoue le DDL `schema_nutriscope.sql`, qui fait
  DROP TABLE IF EXISTS : rechargement complet, jamais de doublon) et `load_products` (une transaction).
- Part du MÊME fichier nettoyé que l'étape `parquet` (source de vérité unique) : les comptages doivent coïncider.
- Identifiants lus dans l'environnement (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD). Le mot de passe n'est
  demandé au clavier que si un terminal est présent ; sinon l'étape échoue avec un message clair
  (une commande unique ou un conteneur ne peuvent pas attendre une saisie). Le mot de passe n'est
  jamais écrit dans un fichier.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import getpass
import sys

from nutriscope.files import StepError, find_input, manifest, rel, write_json
from nutriscope.steps.base import StepResult
from nutriscope.steps.nettoyer import PREFIX as CLEAN_PREFIX


def password(settings) -> str | None:
    if settings.db_password:
        return settings.db_password
    try:
        interactive = sys.stdin is not None and sys.stdin.isatty()
    except Exception:          # flux d'entrée remplacé (tests, conteneur) : pas de saisie possible
        interactive = False
    if interactive:
        return getpass.getpass(f"Mot de passe PostgreSQL ({settings.db_user}@{settings.db_host}) : ") or None
    return None


def run(settings, force: bool = False) -> StepResult:
    clean = find_input(settings.clean_dir, CLEAN_PREFIX, ".parquet", settings.stamp, producer="nettoyer",
                       what="nettoyé (produits_propres_<date>.parquet)")
    secret = password(settings)
    if not secret:
        raise StepError("Mot de passe PostgreSQL absent : définissez DB_PASSWORD (voir .env.example), "
                        "ou lancez sans la base avec « --skip charger_base ».")

    import pandas as pd

    from nutriscope import legacy  # noqa: F401
    from create_database import init_database, load_products
    from options import CONFIG
    from sqlalchemy import text

    df = pd.read_parquet(clean)
    try:
        engine = init_database(CONFIG, settings.db_user, secret, settings.db_host, settings.db_port)
    except Exception as error:
        raise StepError(f"Connexion PostgreSQL impossible ({settings.db_user}@{settings.db_host}:{settings.db_port}) : "
                        f"{error.__class__.__name__}. Vérifiez que le serveur tourne et DB_HOST / DB_PORT / DB_PASSWORD.") from error
    try:
        counts = load_products(engine, df)
        with engine.connect() as connection:
            products = int(connection.execute(text("SELECT count(*) FROM products")).scalar())
    finally:
        engine.dispose()

    if products != len(df):
        raise StepError(f"Contrôle échoué : {products} produits en base pour {len(df)} lignes nettoyées.")
    report = write_json(settings.db_dir / f"base_{settings.stamp}.json", manifest("charger_base", settings, {
        "database": CONFIG["database"]["name"], "host": settings.db_host, "port": settings.db_port,
        "tables": counts,
    }, {
        "input": {"file": rel(clean), "rows": len(df)},
        "controls": {"products_equal_clean_rows": True},
    }))
    return StepResult("charger_base", rows=products, outputs=[rel(report)],
                      message=f"{len(counts)} tables chargées")
