"""
Fiches produits du corpus du RAG (TP du 16/11, bloc 3).

Lit le catalogue nettoyé (par défaut le dernier ``products_clean_<date>.parquet`` du pipeline, les
mêmes produits que la base PostgreSQL ; un CSV nettoyé est aussi accepté), transforme chaque produit
en un texte court et lisible, et écrit :

- ``data/sheets/<code>.txt`` : une fiche par produit ;
- ``data/sheets/metadata.jsonl`` : une ligne JSON par produit. Pour filtrer et citer : ``code``,
  ``name``, ``brand``, ``section``, ``nutriscore`` (lettre), ``incomplete_data``, ``source``. Pour
  rendre la fiche de ``chercher_produit`` sans base SQL (``CATALOG_FIELDS``) : marques, quantité,
  groupes PNNS, labels, score Nutri-Score, NOVA et valeurs pour 100 g. Une valeur absente est ``null``.

Règle héritée du TP 18 : une valeur inconnue s'écrit « non renseigné », jamais 0.

Utilisation ::

    python -m nutriscope.corpus.sheets                     # aussi : python -m nutriscope.pipeline sheets
    python -m nutriscope.corpus.sheets --source data/clean/echantillon_france.csv --export-date 2026-10-06
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import date, datetime
from pathlib import Path

import pandas as pd

from ..options import DATA_PATH, SHARED_DATA_PATH

# Nettoyé du pipeline pour l'échantillon partagé : data/echantillon_france/clean/products_clean_<date>.parquet
PIPELINE_CLEAN_DIR = DATA_PATH / "echantillon_france" / "clean"
PIPELINE_SOURCE = SHARED_DATA_PATH / "echantillon_france.csv"   # sa date sert de date d'export
DEFAULT_OUTPUT = DATA_PATH / "sheets"
METADATA_FILE = "metadata.jsonl"
UNKNOWN = "non renseigné"
SOURCE_LABEL = "Open Food Facts (licence ODbL)"

# Le texte de la fiche est en français : c'est le contenu du corpus, montré et cité aux utilisateurs.
TEMPLATE = """Produit : {product_name} — {brand}
Code-barres : {code}
Rayon : {section}
Nutri-Score : {nutriscore}
Valeurs pour 100 g : énergie {energy_kcal} ; matières grasses {fat}, dont saturées {saturated_fat} ; sucres {sugars} ; sel {salt} ; fibres {fiber} ; protéines {proteins}
Données incomplètes : {incomplete_data}
Source : {source}, export du {export_date}
"""

# Seulement les colonnes utiles du nettoyé (le fichier en compte ~45).
COLUMNS = [
    "code",
    "product_name",
    "brands",
    "pnns_groups_1",
    "pnns_groups_2",
    "nutriscore_grade",
    "nutriscore_score",
    "energy-kcal_100g",
    "fat_100g",
    "saturated-fat_100g",
    "sugars_100g",
    "salt_100g",
    "fiber_100g",
    "proteins_100g",
]
# Colonnes en plus, lues si elles existent : seulement pour les métadonnées (fiche de chercher_produit).
EXTRA_COLUMNS = [
    "quantity",
    "labels_tags",
    "nova_group",
    "energy_100g",
    "carbohydrates_100g",
    "fruits-vegetables-legumes_100g",
]

# Champ des métadonnées -> colonne du nettoyé. Les noms des champs sont ceux des colonnes de la base
# (nutriscope.catalog.DETAIL_COLUMNS) : nutriscope.rag.retriever en refait une ligne du catalogue.
CATALOG_FIELDS = {
    "brands": "brands",
    "quantity": "quantity",
    "pnns_group_1": "pnns_groups_1",
    "pnns_group_2": "pnns_groups_2",
    "labels": "labels_tags",
    "nutriscore_score": "nutriscore_score",
    "nova_group": "nova_group",
    "energy_kcal_100g": "energy-kcal_100g",
    "fat_100g": "fat_100g",
    "saturated_fat_100g": "saturated-fat_100g",
    "sugars_100g": "sugars_100g",
    "salt_100g": "salt_100g",
    "fiber_100g": "fiber_100g",
    "proteins_100g": "proteins_100g",
    "energy_100g": "energy_100g",
    "carbohydrates_100g": "carbohydrates_100g",
    "fruits_vegetables_legumes_100g": "fruits-vegetables-legumes_100g",
}
INTEGER_FIELDS = {"nutriscore_score", "nova_group"}
NUMERIC_FIELDS = {field for field in CATALOG_FIELDS if field.endswith("_100g")} | INTEGER_FIELDS

# Colonne du nutriment -> (champ du gabarit, unité).
NUTRIENTS = {
    "energy-kcal_100g": ("energy_kcal", "kcal"),
    "fat_100g": ("fat", "g"),
    "saturated-fat_100g": ("saturated_fat", "g"),
    "sugars_100g": ("sugars", "g"),
    "salt_100g": ("salt", "g"),
    "fiber_100g": ("fiber", "g"),
    "proteins_100g": ("proteins", "g"),
}

# Valeurs d'Open Food Facts qui signifient « pas de valeur ».
EMPTY_MARKERS = {"", "unknown", "nan", "none", "not-applicable", "not-applicable-category"}


def is_missing(value) -> bool:
    """Vrai pour NaN, None, une chaîne vide et les valeurs OFF comme « unknown »."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return str(value).strip().lower() in EMPTY_MARKERS


def text_or_unknown(value) -> str:
    return UNKNOWN if is_missing(value) else str(value).strip()


def format_number(value, unit: str = "") -> str:
    """Notation décimale française sans zéros inutiles, unité ajoutée seulement à une valeur connue :
    (17.80, "g") -> "17,8 g", (3.0, "g") -> "3 g", (NaN, "g") -> "non renseigné"."""
    if is_missing(value):
        return UNKNOWN
    text = f"{float(value):.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} {unit}" if unit else text


def first_brand(brands) -> str:
    """OFF liste plusieurs marques (« Savencia, St Moret ») : la première est celle du produit."""
    if is_missing(brands):
        return UNKNOWN
    return str(brands).split(",")[0].strip() or UNKNOWN


def section_of(row: pd.Series) -> str:
    """Rayon : groupe PNNS 2 (le plus fin), sinon groupe 1."""
    for column in ("pnns_groups_2", "pnns_groups_1"):
        if not is_missing(row.get(column)):
            return str(row[column]).strip()
    return UNKNOWN


def nutriscore_of(row: pd.Series) -> str:
    """« D (14) », « D » si le score manque, « non renseigné » sans lettre."""
    grade = row.get("nutriscore_grade")
    if is_missing(grade) or str(grade).strip().lower() not in set("abcde"):
        return UNKNOWN
    grade = str(grade).strip().upper()
    score = row.get("nutriscore_score")
    return grade if is_missing(score) else f"{grade} ({int(float(score))})"


def is_incomplete(row: pd.Series) -> bool:
    """Vrai dès qu'un champ de la fiche est « non renseigné »."""
    return (
        any(is_missing(row.get(column)) for column in NUTRIENTS)
        or nutriscore_of(row) == UNKNOWN
        or section_of(row) == UNKNOWN
        or first_brand(row.get("brands")) == UNKNOWN
        or is_missing(row.get("product_name"))
    )


def product_to_sheet(row: pd.Series, export_date: str) -> str:
    """Transforme une ligne du catalogue en texte de fiche."""
    fields = {field: format_number(row.get(column), unit) for column, (field, unit) in NUTRIENTS.items()}
    return TEMPLATE.format(
        product_name=text_or_unknown(row.get("product_name")),
        brand=first_brand(row.get("brands")),
        code=str(row["code"]).strip(),
        section=section_of(row),
        nutriscore=nutriscore_of(row),
        incomplete_data="oui" if is_incomplete(row) else "non",
        source=SOURCE_LABEL,
        export_date=export_date,
        **fields,
    )


def catalog_value(field: str, value):
    """Valeur brute pour les métadonnées : nombre (entier pour le score et NOVA), texte, ou None."""
    if is_missing(value):
        return None
    if field in NUMERIC_FIELDS:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if math.isnan(number):
            return None
        return int(number) if field in INTEGER_FIELDS else number
    return str(value).strip()


def product_metadata(row: pd.Series, export_date: str) -> dict:
    """Une ligne de metadata.jsonl : ce dont le RAG a besoin pour filtrer, citer et rendre une fiche."""
    grade = row.get("nutriscore_grade")
    return {
        "code": str(row["code"]).strip(),
        "name": text_or_unknown(row.get("product_name")),
        "brand": first_brand(row.get("brands")),
        "section": section_of(row),
        "nutriscore": None if is_missing(grade) else str(grade).strip().lower(),
        "incomplete_data": is_incomplete(row),
        "source": f"{SOURCE_LABEL}, export du {export_date}",
        **{field: catalog_value(field, row.get(column)) for field, column in CATALOG_FIELDS.items()},
    }


def latest_pipeline_clean(directory: Path = PIPELINE_CLEAN_DIR) -> Path | None:
    """Le nettoyé le plus récent du pipeline, ou None."""
    files = sorted(directory.glob("products_clean_*.parquet")) if directory.is_dir() else []
    return files[-1] if files else None


def read_catalogue(source: Path) -> pd.DataFrame:
    """Colonnes utiles du nettoyé (Parquet du pipeline ou CSV) ; codes-barres gardés en texte (zéros en tête)."""
    source = Path(source)
    if source.suffix == ".parquet":
        df = pd.read_parquet(source)
    else:
        df = pd.read_csv(source, dtype={"code": str}, encoding="utf-8", low_memory=False)
    missing = [column for column in COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"{source.name}: missing column(s) {', '.join(missing)}")
    df = df[COLUMNS + [column for column in EXTRA_COLUMNS if column in df.columns]].copy()
    df["code"] = df["code"].astype("string")
    df = df.dropna(subset=["code"])
    df["code"] = df["code"].str.strip()
    duplicates = df["code"].duplicated()
    if duplicates.any():
        print(f"{duplicates.sum()} duplicate barcode(s) ignored (first row kept)")
        df = df[~duplicates]
    return df.reset_index(drop=True)


def default_export_date(source: Path) -> str:
    """Sans --export-date : pour un Parquet du pipeline, la date du CSV source du pipeline (le nettoyé
    est daté du jour du nettoyage, pas de l'export) ; sinon celle du fichier lui-même."""
    source = Path(source)
    reference = PIPELINE_SOURCE if source.suffix == ".parquet" and PIPELINE_SOURCE.is_file() else source
    return datetime.fromtimestamp(reference.stat().st_mtime).date().isoformat()


def write_sheets(df: pd.DataFrame, output_dir: Path, export_date: str, clean: bool = True) -> int:
    """Écrit un <code>.txt par produit et metadata.jsonl ; renvoie le nombre de fiches."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if clean:  # les fiches des produits sortis du catalogue doivent disparaître (seulement nos fichiers)
        for old in [*output_dir.glob("*.txt"), output_dir / METADATA_FILE]:
            old.unlink(missing_ok=True)

    with open(output_dir / METADATA_FILE, "w", encoding="utf-8") as metadata:
        for _, row in df.iterrows():
            code = str(row["code"]).strip()
            (output_dir / f"{code}.txt").write_text(product_to_sheet(row, export_date), encoding="utf-8")
            metadata.write(json.dumps(product_metadata(row, export_date), ensure_ascii=False) + "\n")
    return len(df)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Génère une fiche texte par produit pour le corpus du RAG.")
    parser.add_argument("--source", type=Path, default=None,
                        help="catalogue nettoyé, Parquet ou CSV (défaut : dernier nettoyé du pipeline, "
                             "data/echantillon_france/clean/products_clean_<date>.parquet)")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="dossier des fiches")
    parser.add_argument("--export-date", type=date.fromisoformat, default=None,
                        help="date de l'export Open Food Facts (AAAA-MM-JJ) ; par défaut : date du fichier source")
    parser.add_argument("--limit", type=int, default=None, help="seulement les N premiers produits (essais)")
    parser.add_argument("--keep", action="store_true", help="ne vide pas d'abord le dossier de sortie")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.source = args.source or latest_pipeline_clean()
    if args.source is None or not args.source.is_file():
        print(f"Cleaned catalogue not found: {args.source or PIPELINE_CLEAN_DIR} "
              f"(run python -m nutriscope.pipeline clean_data first)")
        return 1
    export_date = args.export_date.isoformat() if args.export_date else default_export_date(args.source)
    df = read_catalogue(args.source)
    if args.limit:
        df = df.head(args.limit)
    count = write_sheets(df, args.output, export_date, clean=not args.keep)
    print(f"{count} sheets written to {args.output} (export of {export_date})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
