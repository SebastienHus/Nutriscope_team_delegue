"""
Création et chargement de la base PostgreSQL NutriScope.

La base ne reçoit que la sortie de `cleaning.clean()` :
- `load_products` refuse un DataFrame dont les codes-barres sont manquants ou non uniques ;
- le DDL (`schema_nutriscope.sql`) porte des contraintes CHECK reprenant les bornes de
  `schema.py` (0–100 g, 0–900 kcal, grades autorisés, code officiel) ;
- le chargement se fait dans une seule transaction : tout ou rien ;
- les tables sont remplies par `COPY … FROM STDIN` (chargement en masse de PostgreSQL,
  via psycopg 3), clés étrangères retirées pendant la copie puis recréées : PostgreSQL les
  vérifie alors en bloc et non ligne par ligne. Extrait complet (16,6 millions de lignes,
  toutes tables confondues) : environ 1 minute, contre 3 avec `COPY` seul et davantage
  avec `to_sql`.

Ce module ne lit ni ne nettoie l'export : la base est chargée par l'étape `load_database`
du pipeline, à partir du Parquet nettoyé (source de vérité unique, partagée avec l'étape
`parquet`), avec contrôle du nombre de produits chargés :

    python -m nutriscope.pipeline load_database            # échantillon partagé
    python -m nutriscope.pipeline load_database --full     # extrait complet

Usage autonome : créer (ou réinitialiser) le schéma, sans données :

    python -m nutriscope.create_database

Identifiants : ceux du conteneur PostgreSQL (`options.db_credentials`) : POSTGRES_USER du `.env`,
mot de passe lu dans `secrets/db_password.txt` (ou POSTGRES_PASSWORD). Aucun mot de passe en argument.
"""

import argparse
import os
import sys

import pandas as pd
import sqlparse
from psycopg import sql
from sqlalchemy import URL, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy_utils import create_database, database_exists

from .options import (CONFIG_PATH, DB_PASSWORD_ENV, DEFAULT_DB_PASSWORD_FILE, ROOT_PATH, db_credentials,
                      read_options)

SQL_SCHEMA_PATH = ROOT_PATH / "schema_nutriscope.sql"
COPY_CHUNKSIZE = 100_000              # lignes converties puis envoyées à COPY par bloc
INTEGER_TYPES = {"smallint", "integer", "bigint"}
DECIMAL_TYPES = {"numeric", "real", "double precision"}
MAX_TAG_LENGTH = 255                  # VARCHAR(255) des tables de référence
INVALID_TAGS = {"xx:none", "en:none", "en:undefined"}
TAG_SEPARATOR = ","

# Colonne du DataFrame nettoyé → colonne de la table
PRODUCT_COLUMNS = {
    "code": "code",
    "product_name": "name",
    "quantity": "quantity",
    "ingredients_text": "ingredients_text",
    "main_category": "main_category",
    "pnns_groups_1": "pnns_group_1",
    "pnns_groups_2": "pnns_group_2",
    "created_t": "created_at",
    "last_modified_t": "last_modified_at",
    "completeness": "completeness",
    "image_url": "image_url",
    "image_small_url": "image_small_url",
    "image_ingredients_url": "image_ingredients_url",
    "image_ingredients_small_url": "image_ingredients_small_url",
    "image_nutrition_url": "image_nutrition_url",
    "image_nutrition_small_url": "image_nutrition_small_url",
}
NUTRITION_COLUMNS = {
    "code": "product_code",
    "energy_100g": "energy_100g",
    "energy-kcal_100g": "energy_kcal_100g",
    "fat_100g": "fat_100g",
    "saturated-fat_100g": "saturated_fat_100g",
    "carbohydrates_100g": "carbohydrates_100g",
    "sugars_100g": "sugars_100g",
    "fiber_100g": "fiber_100g",
    "proteins_100g": "proteins_100g",
    "salt_100g": "salt_100g",
    "sodium_100g": "sodium_100g",
    "fruits-vegetables-legumes_100g": "fruits_vegetables_legumes_100g",
}
SCORE_COLUMNS = {
    "code": "product_code",
    "nutriscore_score": "nutriscore",
    "nutriscore_grade": "nutriscore_grade",
    "nova_group": "nova_group",
    "environmental_score_grade": "environmental_score_grade",
}
# Colonne de tags → (table de référence, table de relation, clé étrangère)
RELATIONSHIPS = {
    "food_groups_tags": ("food_groups", "products_food_groups", "food_group_id"),
    "categories_tags": ("categories", "products_categories", "category_id"),
    "brands_tags": ("brands", "products_brands", "brand_id"),
    "additives_tags": ("additives", "products_additives", "additive_id"),
    "labels_tags": ("labels", "products_labels", "label_id"),
    "allergens": ("allergens", "products_allergens", "allergen_id"),
    "traces_tags": ("traces", "products_traces", "trace_id"),
    "countries_tags": ("countries", "products_countries", "country_id"),
}


# ============================================================================
# INITIALISATION
# ============================================================================

def init_database(config: dict, username: str, password: str,
                  host: str = "localhost", port: int = 5432) -> Engine:
    """Crée la base si besoin et (re)joue le DDL `schema_nutriscope.sql` (script rejouable)."""
    url = URL.create(
        "postgresql+psycopg",
        username=username,
        password=password,
        host=host,
        port=port,
        database=config["database"]["name"],
    )
    engine = create_engine(url)
    if not database_exists(engine.url):
        create_database(engine.url)

    statements = [statement for statement in sqlparse.split(SQL_SCHEMA_PATH.read_text(encoding="utf-8"))
                  if statement.strip()]
    # engine.begin() ouvre une transaction et valide (COMMIT) à la fin du bloc
    with engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
    print(f"Schéma créé : {len(statements)} instructions SQL exécutées.")
    return engine


# ============================================================================
# PRÉPARATION DES TABLES
# ============================================================================

def split_tags(value) -> list[str]:
    """
    Liste de tags Open Food Facts ("en:snacks,en:biscuits") → liste nettoyée : espaces
    retirés, tags vides, trop longs (> 255) ou sans valeur (`xx:none`, `en:undefined`) écartés.
    """
    if not isinstance(value, str):
        return []
    tags = (tag.strip() for tag in value.split(TAG_SEPARATOR))
    return [tag for tag in tags if tag and len(tag) <= MAX_TAG_LENGTH and tag not in INVALID_TAGS]


def build_relationship(df: pd.DataFrame, tag_column: str, foreign_key: str
                       ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Table de référence (`id`, `name`) et table de relation (`product_code`, `<foreign_key>`)
    à partir d'une colonne de tags. Les ids commencent à 1, dans l'ordre d'apparition.

    Un même tag peut apparaître deux fois dans la fiche d'un produit ("en:snacks,en:snacks") :
    les couples (produit, tag) sont donc rendus uniques.
    """
    pairs = (
        df[["code", tag_column]]
        .assign(**{tag_column: df[tag_column].map(split_tags)})
        .explode(tag_column)
        .dropna(subset=[tag_column])
        .drop_duplicates()
    )
    names = pd.Index(pairs[tag_column].unique())
    reference = pd.DataFrame({"id": range(1, len(names) + 1), "name": names})
    relation = pd.DataFrame({
        "product_code": pairs["code"].to_numpy(),
        foreign_key: names.get_indexer(pairs[tag_column]) + 1,
    })
    return relation, reference


def _select(df: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """Colonnes renommées pour la table ; une colonne absente de l'export devient NULL."""
    return df.reindex(columns=list(columns)).rename(columns=columns)


def prepare_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    Découpe le DataFrame nettoyé en tables, dans l'ordre d'insertion imposé par les clés
    étrangères : produits, nutrition, scores, tables de référence, puis relations.
    Les colonnes de tags absentes de l'export (ex. échantillon) sont ignorées.

    Lève `ValueError` si un code-barres manque ou apparaît deux fois : la base ne reçoit
    que la sortie de `cleaning.clean()`.
    """
    if df["code"].isna().any():
        raise ValueError("Chargement refusé : des produits n'ont pas de code-barres.")
    if not df["code"].is_unique:
        duplicates = df.loc[df["code"].duplicated(), "code"].nunique()
        raise ValueError(f"Chargement refusé : {duplicates} codes-barres en double.")

    tables = {
        "products": _select(df, PRODUCT_COLUMNS),
        "nutrition": _select(df, NUTRITION_COLUMNS),
        "score": _select(df, SCORE_COLUMNS),
    }
    relations = {}
    for tag_column, (reference_table, relation_table, foreign_key) in RELATIONSHIPS.items():
        if tag_column not in df.columns:
            continue
        relations[relation_table], tables[reference_table] = build_relationship(df, tag_column, foreign_key)
    return {**tables, **relations}


# ============================================================================
# CHARGEMENT
# ============================================================================

def _column_types(cursor, table: str) -> dict[str, str]:
    """Type PostgreSQL de chaque colonne d'une table (`information_schema`)."""
    cursor.execute(
        "SELECT column_name, data_type FROM information_schema.columns "
        "WHERE table_schema = current_schema() AND table_name = %s",
        (table,),
    )
    return dict(cursor.fetchall())


def _copy_values(series: pd.Series, sql_type: str) -> list:
    """
    Colonne → valeurs Python natives pour COPY, un manquant devenant `None`.

    COPY ne convertit rien : un score lu en flottant (`3.0`) serait refusé par une colonne
    INTEGER. Les entiers sont donc arrondis puis typés `Int64`, les décimaux passés en
    flottants, les dates en `datetime` ; le texte est transmis tel quel.
    """
    if sql_type in INTEGER_TYPES:
        values = pd.to_numeric(series).round().astype("Int64")
    elif sql_type in DECIMAL_TYPES:
        values = pd.to_numeric(series).astype("float64")
    elif sql_type.startswith("timestamp"):
        values = pd.to_datetime(series)
    else:
        values = series
    return values.astype(object).where(values.notna(), None).tolist()


def copy_table(cursor, name: str, table: pd.DataFrame, chunksize: int = COPY_CHUNKSIZE) -> None:
    """
    Remplit la table `name` avec `table` par `COPY … FROM STDIN`, bloc par bloc (la
    conversion en objets Python reste bornée à `chunksize` lignes). Lève `ValueError` si
    une colonne du DataFrame n'existe pas dans la table.
    """
    types = _column_types(cursor, name)
    unknown = [column for column in table.columns if column not in types]
    if unknown:
        raise ValueError(f"Colonnes absentes de la table {name} : {', '.join(unknown)}")

    statement = sql.SQL("COPY {} ({}) FROM STDIN").format(
        sql.Identifier(name), sql.SQL(", ").join(map(sql.Identifier, table.columns)))
    with cursor.copy(statement) as copy:
        for start in range(0, len(table), chunksize):
            chunk = table.iloc[start:start + chunksize]
            columns = [_copy_values(chunk[column], types[column]) for column in chunk.columns]
            for row in zip(*columns):
                copy.write_row(row)


def _foreign_keys(cursor, tables) -> list[tuple[str, str, str]]:
    """Clés étrangères des `tables` : (table, nom de la contrainte, définition SQL)."""
    cursor.execute(
        "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) FROM pg_constraint "
        "WHERE contype = 'f' AND connamespace = current_schema()::regnamespace "
        "AND conrelid::regclass::text = ANY(%s) ORDER BY conrelid::regclass::text, conname",
        (list(tables),),
    )
    return cursor.fetchall()


def load_products(engine: Engine, df: pd.DataFrame) -> dict[str, int]:
    """
    Charge le DataFrame nettoyé dans la base, en une seule transaction, table par table
    par `COPY`.

    Les clés étrangères sont retirées avant la copie puis recréées : `ADD CONSTRAINT`
    vérifie toutes les lignes d'un coup (jointure) au lieu d'un contrôle par ligne insérée,
    trois fois plus lent. Rien n'est relâché : une ligne orpheline fait échouer la
    recréation, donc toute la transaction, et les CHECK s'appliquent pendant la copie.
    Un `VACUUM ANALYZE` suit le chargement (statistiques, index de recherche).

    Les tables doivent être vides (`init_database` les recrée). Retourne le nombre de lignes
    insérées par table, pour le journal.
    """
    tables = prepare_tables(df)
    reference_tables = [reference for reference, _, _ in RELATIONSHIPS.values() if reference in tables]

    with engine.begin() as connection:
        with connection.connection.cursor() as cursor:
            foreign_keys = _foreign_keys(cursor, tables)
            for table, constraint, _ in foreign_keys:
                cursor.execute(sql.SQL("ALTER TABLE {} DROP CONSTRAINT {}").format(
                    sql.Identifier(table), sql.Identifier(constraint)))
            for name, table in tables.items():
                copy_table(cursor, name, table)
            for table, constraint, definition in foreign_keys:
                cursor.execute(sql.SQL("ALTER TABLE {} ADD CONSTRAINT {} ").format(
                    sql.Identifier(table), sql.Identifier(constraint)) + sql.SQL(definition))
        # Les ids ont été fournis explicitement : on recale les séquences SERIAL
        for name in reference_tables:
            connection.execute(text(
                f"SELECT setval(pg_get_serial_sequence('{name}', 'id'), "
                f"COALESCE(MAX(id), 0) + 1, false) FROM {name}"
            ))

    # Hors transaction (VACUUM l'exige) : statistiques à jour pour le planificateur, et liste
    # d'attente des index trigrammes vidée (sans cela, une recherche par nom est 50 fois plus lente).
    # PARALLEL 0 : un VACUUM parallèle partage sa mémoire de travail (64 Mo) par /dev/shm, que Docker
    # limite à 64 Mo par défaut ("could not resize shared memory segment").
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("VACUUM (ANALYZE, PARALLEL 0)"))

    return {name: len(table) for name, table in tables.items()}


def main(args):
    filename = os.path.abspath(args.filename)
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Le chemin n'existe pas : `{filename}`")
    config = read_options(filename)
    credentials = db_credentials()
    if credentials is None:
        raise SystemExit(
            f"Aucun mot de passe PostgreSQL : définir {DB_PASSWORD_ENV} ou créer "
            f"{DEFAULT_DB_PASSWORD_FILE} (scripts/init-secrets.ps1)"
        )
    # Les options de la ligne de commande priment sur le .env
    overrides = {"username": args.username, "host": args.host, "port": args.port}
    credentials.update({key: value for key, value in overrides.items() if value is not None})
    engine = init_database(config, **credentials)
    engine.dispose()
    print("Base prête et vide : chargement avec `python -m nutriscope.pipeline load_database`.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="NutriscopeDatabaseCreation",
        description="Crée (ou réinitialise) la base NutriScope et son schéma, sans données. "
                    "Chargement : python -m nutriscope.pipeline load_database",
    )
    parser.add_argument("filename", nargs="?", default=CONFIG_PATH,
                        help="Fichier d'options (par défaut : options.ini du package)")
    parser.add_argument("-u", "--username", default=None, help="Défaut : POSTGRES_USER du .env")
    parser.add_argument("--host", default=None, help="Défaut : POSTGRES_HOST, sinon localhost")
    parser.add_argument("--port", type=int, default=None, help="Défaut : POSTGRES_PORT, sinon 5432")
    args = parser.parse_args()
    sys.exit(main(args))
