"""
Conversion du catalogue nettoyé en Parquet partitionné par rayon — TP 12.

Lit la sortie de `cleaning.clean()` (CSV ou Parquet), pose les types colonne par colonne,
ajoute la clé de partition `pnns_group` (slug de `pnns_groups_1`, `unknown` si vide) et
écrit `data/parquet/products/pnns_group=<slug>/…` en Parquet compressé ZSTD. Le schéma
(type et justification de chaque colonne, clé de partition, compression, nombre de lignes,
licence) est écrit à côté du dossier, dans `schema_products.json`.

La conversion est rejouable et idempotente : le dossier cible est supprimé avant chaque
écriture (aucune partition orpheline ne subsiste), les lignes sont triées par code et
écrites sur un seul thread (mêmes octets à chaque exécution). Un marqueur `_SUCCESS` est
écrit en dernier dans le dossier : un dossier sans marqueur est une écriture interrompue.

    python -m nutriscope.storage.convert_parquet
    python -m nutriscope.storage.convert_parquet data/clean/echantillon.csv data/parquet/products

Données : © Open Food Facts contributors — ODbL.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path

import duckdb

from ..cleaning import MISSING_FLAG_SUFFIX, NUTRIENT_SUFFIX, TIMESTAMP_COLUMNS
from ..options import DATA_PATH, ROOT_PATH
from ..schema import UNKNOWN_GROUP

# ============================================================================
# CONSTANTES
# ============================================================================

DEFAULT_SOURCE = DATA_PATH / "clean" / "en.openfoodfacts.org.products.csv"
DEFAULT_DESTINATION = DATA_PATH / "parquet" / "products"
SCHEMA_FILENAME = "schema_products.json"
SUCCESS_MARKER = "_SUCCESS"                          # écrit en dernier : le dossier est complet

VIEW_NAME = "products"
GROUP_COLUMN = "pnns_groups_1"
PARTITION_COLUMN = "pnns_group"
COMPRESSION = "zstd"
LICENSE = "© Open Food Facts contributors — Open Database License (ODbL) 1.0"

# Types posés explicitement, avec leur justification (écrite dans le schéma)
CODE_TYPE = ("VARCHAR", "Texte : un code-barres n'est pas un nombre, les zéros de tête doivent survivre.")
INTEGER_TYPES = {
    "additives_n": ("SMALLINT", "Entier : nombre d'additifs (quelques dizaines au plus)."),
    "nutriscore_score": ("SMALLINT", "Entier : score Nutri-Score, de -15 à 40 environ."),
    "nova_group": ("TINYINT", "Entier : groupe NOVA de 1 à 4, un octet suffit."),
}
TIMESTAMP_TYPE = ("TIMESTAMP", "Date : convertie depuis le timestamp Unix par le nettoyage.")
BOOLEAN_TYPE = ("BOOLEAN", "Drapeau posé par le nettoyage (catégorie vide ou nutriment manquant).")
FLOAT_TYPE = ("FLOAT", "Réel simple précision : valeurs ≤ 3 766 à deux décimales, deux fois moins "
                       "de place qu'un DOUBLE pour une précision suffisante.")
TEXT_TYPE = ("VARCHAR", "Texte libre, tags ou modalité.")
BOOLEAN_COLUMNS = ("empty_category",)
PARTITION_JUSTIFICATION = (f"Clé de partition : slug de `{GROUP_COLUMN}` (`{UNKNOWN_GROUP}` si vide), "
                           "lue depuis le chemin `pnns_group=<slug>`.")


# ============================================================================
# OUTILS SQL
# ============================================================================

def sql_string(value: str | Path) -> str:
    """Littéral SQL entre apostrophes ; un chemin est rendu absolu, au format POSIX."""
    if isinstance(value, Path):
        value = value.resolve().as_posix()
    return "'" + value.replace("'", "''") + "'"


def sql_identifier(name: str) -> str:
    """Identifiant SQL entre guillemets (les noms comme `energy-kcal_100g` contiennent un tiret)."""
    return '"' + name.replace('"', '""') + '"'


def column_type(column: str) -> tuple[str, str]:
    """Type DuckDB d'une colonne du catalogue nettoyé et justification d'une ligne."""
    if column == "code":
        return CODE_TYPE
    if column in INTEGER_TYPES:
        return INTEGER_TYPES[column]
    if column in TIMESTAMP_COLUMNS:
        return TIMESTAMP_TYPE
    if column in BOOLEAN_COLUMNS or column.endswith(MISSING_FLAG_SUFFIX):
        return BOOLEAN_TYPE
    if column.endswith(NUTRIENT_SUFFIX) or column == "completeness":
        return FLOAT_TYPE
    return TEXT_TYPE


def source_relation(source: Path) -> str:
    """
    Relation DuckDB qui lit la source. Le CSV est lu entièrement en texte (`all_varchar`) :
    les types sont posés ensuite par des `CAST` explicites, jamais devinés.
    """
    if source.suffix == ".parquet":
        return f"read_parquet({sql_string(source)})"
    return f"read_csv({sql_string(source)}, header = true, all_varchar = true)"


def partition_expression(column: str = GROUP_COLUMN) -> str:
    """Slug du rayon : minuscules, tout caractère non alphanumérique → `-` ; vide ou NULL → `unknown`."""
    group = f"coalesce(nullif(trim({sql_identifier(column)}), ''), '{UNKNOWN_GROUP}')"
    return f"trim(regexp_replace(lower({group}), '[^a-z0-9]+', '-', 'g'), '-')"


def relative_path(path: Path) -> str:
    """Chemin relatif à la racine du dépôt quand c'est possible (schéma lisible d'une machine à l'autre)."""
    path = path.resolve()
    try:
        return path.relative_to(ROOT_PATH).as_posix()
    except ValueError:
        return path.as_posix()


# ============================================================================
# CONVERSION
# ============================================================================

def is_complete(root: Path) -> bool:
    """Vrai si le dossier partitionné porte son marqueur `_SUCCESS` (écriture terminée)."""
    return (Path(root) / SUCCESS_MARKER).is_file()


def open_products(con: duckdb.DuckDBPyConnection, root: Path = DEFAULT_DESTINATION,
                  view: str = VIEW_NAME) -> None:
    """Crée (ou remplace) la vue `products` sur le jeu partitionné, clé de partition en texte."""
    pattern = (Path(root).resolve() / "**" / "*.parquet").as_posix()
    con.execute(
        f"CREATE OR REPLACE VIEW {view} AS SELECT * FROM read_parquet({sql_string(pattern)}, "
        f"hive_partitioning = true, hive_types = {{'{PARTITION_COLUMN}': VARCHAR}})"
    )


def to_parquet(source: Path = DEFAULT_SOURCE, destination: Path = DEFAULT_DESTINATION,
               schema_path: Path | None = None) -> Path:
    """
    Source nettoyée → Parquet partitionné par rayon, puis son schéma, puis `_SUCCESS`.

    Le schéma est écrit dans `schema_path` (par défaut `schema_products.json` à côté du
    dossier). Le dossier cible est supprimé avant l'écriture (conversion rejouable). Lève
    `FileNotFoundError` si la source manque et `ValueError` si `pnns_groups_1` est absente.
    Retourne le chemin du schéma écrit.
    """
    source, destination = Path(source), Path(destination)
    schema_path = destination.parent / SCHEMA_FILENAME if schema_path is None else Path(schema_path)
    if not source.exists():
        raise FileNotFoundError(f"Source not found: {relative_path(source)}")

    con = duckdb.connect()
    try:
        con.execute("SET threads = 1")           # écriture déterministe : mêmes octets à chaque exécution
        relation = source_relation(source)
        columns = [row[0] for row in con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()]
        if GROUP_COLUMN not in columns:
            raise ValueError(f"Missing column in source: {GROUP_COLUMN}")

        casts = ",\n    ".join(
            f"CAST({sql_identifier(column)} AS {column_type(column)[0]}) AS {sql_identifier(column)}"
            for column in columns
        )

        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)   # COPY ne crée pas les parents

        con.execute(f"""
            COPY (
                SELECT
                    {casts},
                    {partition_expression()} AS {PARTITION_COLUMN}
                FROM {relation}
                ORDER BY {sql_identifier("code")}
            )
            TO {sql_string(destination)}
            (FORMAT PARQUET, PARTITION_BY ({PARTITION_COLUMN}), COMPRESSION {COMPRESSION.upper()},
             OVERWRITE_OR_IGNORE)
        """)

        written = write_schema(con, source, destination, schema_path)
    finally:
        con.close()

    (destination / SUCCESS_MARKER).touch()      # en dernier : le dossier est complet
    return written


def write_schema(con: duckdb.DuckDBPyConnection, source: Path, destination: Path,
                 schema_path: Path | None = None) -> Path:
    """
    Écrit le schéma du dossier partitionné (`schema_products.json` à côté par défaut).
    Les types sont relus dans les Parquet écrits (pas recopiés de la requête) ; pas
    d'horodatage : le fichier est réécrit avec le Parquet à chaque conversion.
    """
    open_products(con, destination)
    row_count = con.execute(f"SELECT count(*) FROM {VIEW_NAME}").fetchone()[0]
    partitions = con.execute(
        f"SELECT {PARTITION_COLUMN}, count(*) FROM {VIEW_NAME} GROUP BY 1 ORDER BY 1"
    ).fetchall()
    described = con.execute(f"DESCRIBE {VIEW_NAME}").fetchall()

    columns = []
    for name, sql_type, *_ in described:
        justification = PARTITION_JUSTIFICATION if name == PARTITION_COLUMN else column_type(name)[1]
        columns.append({"name": name, "type": sql_type, "justification": justification})

    schema = {
        "dataset": relative_path(destination),
        "source": relative_path(source),
        "format": "parquet",
        "partition_key": {
            "name": PARTITION_COLUMN,
            "source_column": GROUP_COLUMN,
            "expression": partition_expression(),
        },
        "compression": COMPRESSION,
        "row_count": row_count,
        "partitions": {group: count for group, count in partitions},
        "columns": columns,
        "license": LICENSE,
    }

    schema_path = destination.parent / SCHEMA_FILENAME if schema_path is None else Path(schema_path)
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return schema_path


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Convert the cleaned catalogue to Parquet partitioned by PNNS group.")
    parser.add_argument("source", nargs="?", type=Path, default=DEFAULT_SOURCE,
                        help="Cleaned CSV or Parquet (output of cleaning.clean())")
    parser.add_argument("destination", nargs="?", type=Path, default=DEFAULT_DESTINATION,
                        help="Partitioned Parquet folder (deleted then rewritten)")
    args = parser.parse_args()

    try:
        schema_path = to_parquet(args.source, args.destination)
    except (FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    print(f"{schema['row_count']:,} rows, {len(schema['partitions'])} partitions -> {args.destination}")
    print(f"Schema -> {schema_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
