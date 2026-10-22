"""
Export d'entraînement figé pour la prédiction du Nutri-Score — TP 12.

Lit le Parquet partitionné produit par `convert_parquet.py`, ne garde que les produits
utilisables pour prédire le Nutri-Score, et écrit :

- `data/exports/features_nutriscore_<AAAAMMJJ>.parquet` : identifiant, rayon, nutriments,
  `additives_n`, `nova_group`, trois ratios, `nutriscore_score` et la cible `nutriscore_grade` ;
- `data/exports/features_nutriscore_<AAAAMMJJ>.schema.json` : le contrat de cet export
  (date de gel, source, commit, nombre de lignes, SHA-256, filtres, répartition de la cible,
  description et politique de manquants de chaque colonne, licence, usage prévu).

Un produit est utilisable si son grade est a-e, si ses sept nutriments clés sont présents
et s'il respecte les cohérences du nettoyage (`schema.sugars_within_carbohydrates`,
`schema.saturated_within_fat`, même marge de 0,5 g) avec une énergie strictement positive.

L'export est figé : il refuse d'écraser un fichier existant (`FileExistsError`), sauf avec
`--force`. Les lignes sont triées par code et écrites sur un seul thread : relancer avec
`--force` sur le même Parquet produit la même empreinte SHA-256. Le split train / test
n'est pas fait ici (TP 13).

    python src/storage/export_features.py
    python src/storage/export_features.py -i data/parquet/products -o data/exports --force

Données : © Open Food Facts contributors — ODbL.
"""

import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb

# Les scripts de `src/` s'importent à plat (`import schema`), comme dans `pipeline.py`
SRC_PATH = Path(__file__).resolve().parents[1]
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from options import DATA_PATH  # noqa: E402
from schema import KCAL_PER_GRAM, KEY_NUTRIENTS, NUTRISCORE_GRADES, ROUNDING_TOLERANCE_G  # noqa: E402
from storage.convert_parquet import (  # noqa: E402
    DEFAULT_DESTINATION,
    LICENSE,
    PARTITION_COLUMN,
    ROOT_PATH,
    VIEW_NAME,
    open_products,
    relative_path,
    sql_identifier,
    sql_string,
)

# ============================================================================
# CONSTANTES
# ============================================================================

DEFAULT_SOURCE = DEFAULT_DESTINATION                 # le Parquet partitionné de la conversion
DEFAULT_OUTPUT_DIR = DATA_PATH / "exports"
FILE_PREFIX = "features_nutriscore_"
SCHEMA_SUFFIX = ".schema.json"
COMPRESSION = "zstd"
HASH_BLOCK_SIZE = 1 << 20                            # 1 Mo par lecture pour le SHA-256

ID_COLUMN = "code"
TARGET = "nutriscore_grade"
SCORE = "nutriscore_score"
TARGET_GRADES = tuple(grade for grade in NUTRISCORE_GRADES if grade != "not-applicable")

KCAL = "energy-kcal_100g"
FAT_KCAL_PER_GRAM = KCAL_PER_GRAM["fat_100g"]

INTENDED_USE = ("Entraînement et évaluation des modèles de prédiction du Nutri-Score "
                "(classification du grade, régression du score) — TP 13 (split) et TP 14.")
NO_MISSING = "Aucun manquant : filtré à l'export."


@dataclass(frozen=True)
class Feature:
    """Colonne de l'export : son unité, sa description, sa politique de manquants et,
    pour une colonne calculée, son expression SQL."""
    name: str
    unit: str | None
    description: str
    missing_policy: str
    expression: str | None = None


def _ratio(numerator: str, denominator: str, factor: float = 1.0) -> str:
    """Ratio en FLOAT, 0 si le dénominateur est nul."""
    num, den = sql_identifier(numerator), sql_identifier(denominator)
    scaled = f"{num} * {factor!r}" if factor != 1.0 else num
    return f"CAST(CASE WHEN {den} > 0 THEN {scaled} / {den} ELSE 0 END AS FLOAT)"


NUTRIENT_DESCRIPTIONS = {
    "energy-kcal_100g": ("kcal/100 g", "Énergie."),
    "fat_100g": ("g/100 g", "Lipides."),
    "saturated-fat_100g": ("g/100 g", "Acides gras saturés."),
    "carbohydrates_100g": ("g/100 g", "Glucides."),
    "sugars_100g": ("g/100 g", "Sucres."),
    "proteins_100g": ("g/100 g", "Protéines."),
    "salt_100g": ("g/100 g", "Sel."),
}

# Ordre des colonnes de l'export (le schéma JSON suit le même ordre)
FEATURES = (
    Feature(ID_COLUMN, None, "Code-barres du produit : identifiant, pas une feature.",
            "Aucun manquant : identifiant obligatoire et unique."),
    Feature(PARTITION_COLUMN, None, "Rayon : slug de `pnns_groups_1`, clé de partition du Parquet.",
            "Aucun manquant : `unknown` posé à la conversion. Encodage catégoriel au TP 14."),
    *(Feature(name, *NUTRIENT_DESCRIPTIONS[name], NO_MISSING) for name in KEY_NUTRIENTS),
    Feature("additives_n", "nombre", "Nombre d'additifs déclarés.",
            "Manquants possibles (liste d'ingrédients absente) : indicateur de manquant et "
            "imputation au TP 14, calculée sur le train après le split."),
    Feature("nova_group", "groupe 1-4", "Groupe NOVA de transformation.",
            "Manquants possibles : modalité dédiée « inconnu » au TP 14."),
    Feature("ratio_sugars_carbs", "ratio", "Part des sucres dans les glucides (sucres / glucides), "
            "0 si glucides nuls. Peut dépasser 1 de peu (marge de 0,5 g du nettoyage).",
            "Aucun manquant : calculé sur des nutriments présents.",
            _ratio("sugars_100g", "carbohydrates_100g")),
    Feature("ratio_satfat_fat", "ratio", "Part des saturés dans les lipides (saturés / lipides), "
            "0 si lipides nuls. Peut dépasser 1 de peu (marge de 0,5 g du nettoyage).",
            "Aucun manquant : calculé sur des nutriments présents.",
            _ratio("saturated-fat_100g", "fat_100g")),
    Feature("ratio_energy_fat", "ratio", "Part de l'énergie venant des lipides (lipides × 9 / kcal).",
            "Aucun manquant : énergie strictement positive.",
            _ratio("fat_100g", KCAL, FAT_KCAL_PER_GRAM)),
    Feature(SCORE, "points", "Score Nutri-Score officiel : cible secondaire (régression).",
            "Manquants possibles : lignes écartées pour la régression. Ne pas l'utiliser comme "
            "feature pour prédire le grade : le grade en est dérivé (fuite de cible)."),
    Feature(TARGET, "grade a-e", "Grade Nutri-Score : cible principale (classification).", NO_MISSING),
)

FILTERS = (
    f"`{TARGET}` dans {list(TARGET_GRADES)}",
    f"sept nutriments clés présents : {list(KEY_NUTRIENTS)}",
    f"sucres ≤ glucides + {ROUNDING_TOLERANCE_G} g (schema.sugars_within_carbohydrates)",
    f"saturés ≤ lipides + {ROUNDING_TOLERANCE_G} g (schema.saturated_within_fat)",
    f"`{KCAL}` > 0",
)


# ============================================================================
# REQUÊTE
# ============================================================================

def required_columns() -> list[str]:
    """Colonnes que le Parquet source doit contenir."""
    return [feature.name for feature in FEATURES if feature.expression is None]


def features_query() -> str:
    """Requête de l'export : filtres de `FILTERS`, colonnes de `FEATURES`, tri par code."""
    columns = ",\n    ".join(
        f"{feature.expression} AS {sql_identifier(feature.name)}" if feature.expression
        else sql_identifier(feature.name)
        for feature in FEATURES
    )
    grades = ", ".join(sql_string(grade) for grade in TARGET_GRADES)
    present = "\n  AND ".join(f"{sql_identifier(column)} IS NOT NULL" for column in KEY_NUTRIENTS)
    tolerance = repr(ROUNDING_TOLERANCE_G)
    return f"""
SELECT
    {columns}
FROM {VIEW_NAME}
WHERE {sql_identifier(TARGET)} IN ({grades})
  AND {present}
  AND "sugars_100g" <= "carbohydrates_100g" + {tolerance}
  AND "saturated-fat_100g" <= "fat_100g" + {tolerance}
  AND {sql_identifier(KCAL)} > 0
ORDER BY {sql_identifier(ID_COLUMN)}
"""


# ============================================================================
# MÉTADONNÉES
# ============================================================================

def sha256(path: Path) -> str:
    """Empreinte SHA-256 d'un fichier."""
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for block in iter(lambda: file.read(HASH_BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT_PATH, capture_output=True,
                          text=True, check=True).stdout.strip()


def git_commit() -> str:
    """Commit Git courant du dépôt, suffixé de `-dirty` si l'arbre de travail est modifié."""
    try:
        commit = _git("rev-parse", "HEAD")
        return f"{commit}-dirty" if _git("status", "--porcelain") else commit
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def export_paths(output_dir: Path, freeze_date: date) -> tuple[Path, Path]:
    """Chemins du Parquet daté et de son schéma."""
    parquet_path = Path(output_dir) / f"{FILE_PREFIX}{freeze_date:%Y%m%d}.parquet"
    return parquet_path, parquet_path.with_suffix(SCHEMA_SUFFIX)


def describe_export(con: duckdb.DuckDBPyConnection, parquet_path: Path, source: Path,
                    freeze_date: date) -> dict:
    """Contrat de l'export, relu dans le Parquet écrit (types, manquants, répartition de la cible)."""
    relation = f"read_parquet({sql_string(parquet_path)})"
    described = con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()
    names = [row[0] for row in described]
    expected = [feature.name for feature in FEATURES]
    if names != expected:
        raise RuntimeError(f"Exported columns {names} differ from the declared features {expected}")

    counts = con.execute(
        "SELECT count(*), " + ", ".join(f"count({sql_identifier(name)})" for name in names)
        + f" FROM {relation}"
    ).fetchone()
    row_count, present = counts[0], counts[1:]
    distribution = dict(con.execute(
        f"SELECT {sql_identifier(TARGET)}, count(*) FROM {relation} GROUP BY 1 ORDER BY 1"
    ).fetchall())

    def percent(count: int) -> float:
        return round(100 * count / row_count, 2) if row_count else 0.0

    columns = [
        {
            "name": feature.name,
            "type": sql_type,
            "unit": feature.unit,
            "description": feature.description,
            "missing_pct": percent(row_count - count),
            "missing_policy": feature.missing_policy,
        }
        for feature, (_, sql_type, *_details), count in zip(FEATURES, described, present)
    ]

    return {
        "name": parquet_path.name,
        "freeze_date": freeze_date.isoformat(),
        "source": relative_path(source),
        "git_commit": git_commit(),
        "row_count": row_count,
        "sha256": sha256(parquet_path),
        "target": TARGET,
        "identifier": ID_COLUMN,
        "filters": list(FILTERS),
        "target_distribution": {
            grade: {"count": distribution.get(grade, 0), "pct": percent(distribution.get(grade, 0))}
            for grade in TARGET_GRADES
        },
        "columns": columns,
        "license": LICENSE,
        "intended_use": INTENDED_USE,
    }


# ============================================================================
# EXPORT
# ============================================================================

def export_features(source: Path = DEFAULT_SOURCE, output_dir: Path = DEFAULT_OUTPUT_DIR,
                    force: bool = False, freeze_date: date | None = None) -> tuple[Path, Path]:
    """
    Écrit l'export daté et son schéma ; retourne leurs chemins.

    Lève `FileExistsError` si l'export du jour existe déjà et que `force` est faux,
    `FileNotFoundError` si le Parquet source manque, `ValueError` s'il lui manque une colonne.
    """
    source, output_dir = Path(source), Path(output_dir)
    freeze_date = date.today() if freeze_date is None else freeze_date
    parquet_path, schema_path = export_paths(output_dir, freeze_date)

    if parquet_path.exists() and not force:
        raise FileExistsError(f"{parquet_path} already exists (use --force to overwrite)")
    if not source.is_dir() or not any(source.rglob("*.parquet")):
        raise FileNotFoundError(f"No Parquet dataset found in {source}")

    con = duckdb.connect()
    try:
        con.execute("SET threads = 1")           # écriture déterministe : même SHA-256 à chaque exécution
        open_products(con, source)
        available = {row[0] for row in con.execute(f"DESCRIBE {VIEW_NAME}").fetchall()}
        missing = [column for column in required_columns() if column not in available]
        if missing:
            raise ValueError(f"Missing columns in {source}: {missing}")

        output_dir.mkdir(parents=True, exist_ok=True)
        parquet_path.unlink(missing_ok=True)
        con.execute(f"COPY ({features_query()}) TO {sql_string(parquet_path)} "
                    f"(FORMAT PARQUET, COMPRESSION {COMPRESSION.upper()})")

        contract = describe_export(con, parquet_path, source, freeze_date)
    finally:
        con.close()

    schema_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return parquet_path, schema_path


# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description="Frozen, dated training export for Nutri-Score prediction.")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_SOURCE,
                        help="Partitioned Parquet folder (output of convert_parquet.py)")
    parser.add_argument("--output-dir", "-o", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Destination folder of the export and its schema")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Overwrite today's export if it already exists")
    args = parser.parse_args()

    # TODO: enlever grade unknown, not-applicable + ajouter colonne split avant la conversion en parquet
    try:
        parquet_path, schema_path = export_features(args.input, args.output_dir, args.force)
    except (FileExistsError, FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    contract = json.loads(schema_path.read_text(encoding="utf-8"))
    print(f"{contract['row_count']:,} rows -> {parquet_path}")
    print(f"Schema -> {schema_path} (sha256 {contract['sha256'][:12]}...)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
