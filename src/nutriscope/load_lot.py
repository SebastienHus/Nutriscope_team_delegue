"""
Ajoute au catalogue PostgreSQL les fiches Open Food Facts du lot de l'atelier scanner
(``data/catalogue_off_lot.csv``), pour que ``chercher_produit`` puisse les retrouver (palier 3).

    python -m nutriscope.load_lot                       # data/catalogue_off_lot.csv
    python -m nutriscope.load_lot chemin/vers/lot.csv

Règle du brief : on ajoute les produits **qui ne sont pas déjà** dans la base ; une fiche déjà
chargée par le pipeline n'est pas modifiée. Tout se fait dans une seule transaction.

Correspondances : rayon inconnu (``pnns_group_1 = 'unknown'``), dates = ``extrait_le``, marques
écrites comme les tags du pipeline (minuscules, sans accents, espaces remplacés par des tirets).
Une case vide reste NULL, jamais 0.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

from .catalog import normalize_text
from .options import CONFIG, ROOT_PATH, db_credentials

DEFAULT_PATH = ROOT_PATH / "data" / "catalogue_off_lot.csv"
EXPECTED_COLUMNS = {"code", "nom", "marque", "nutriscore", "kj", "kcal", "lipides", "satures", "glucides",
                    "sucres", "fibres", "proteines", "sel", "ingredients", "extrait_le"}
# Colonne du lot -> colonne de la table `nutrition`
NUTRITION = {"kj": "energy_100g", "kcal": "energy_kcal_100g", "lipides": "fat_100g",
             "satures": "saturated_fat_100g", "glucides": "carbohydrates_100g", "sucres": "sugars_100g",
             "fibres": "fiber_100g", "proteines": "proteins_100g", "sel": "salt_100g"}


def brand_tag(name: str) -> str:
    """« Bonne Maman » -> « bonne-maman », comme les tags de marque du pipeline."""
    return re.sub(r"[^a-z0-9]+", "-", normalize_text(name)).strip("-")


def number(value: str) -> float | None:
    """Case du CSV -> nombre, ou None si elle est vide (jamais 0)."""
    value = (value or "").strip().replace(",", ".")
    return float(value) if value else None


def read_lot(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        missing = EXPECTED_COLUMNS - set(reader.fieldnames or [])
        if missing:
            raise SystemExit(f"{path.name} n'a pas les colonnes du lot (manquent : {', '.join(sorted(missing))}). "
                             "Vérifiez que c'est bien catalogue_off_lot.csv, et non un autre fichier du lot.")
        return list(reader)


def load_lot(path: Path = DEFAULT_PATH, engine=None) -> dict[str, int]:
    """Insère les produits absents de la base. Rend {"lus", "ajoutes", "deja_presents"}."""
    from sqlalchemy import URL, create_engine, text

    rows = read_lot(Path(path))
    if engine is None:
        credentials = db_credentials()
        if credentials is None:
            raise SystemExit("Aucun mot de passe PostgreSQL : POSTGRES_PASSWORD ou secrets/db_password.txt")
        engine = create_engine(URL.create("postgresql+psycopg", username=credentials["username"],
                                          password=credentials["password"], host=credentials["host"],
                                          port=credentials["port"], database=CONFIG["database"]["name"]))
    added = 0
    with engine.begin() as connection:
        for row in rows:
            code = row["code"].strip()
            inserted = connection.execute(text(
                "INSERT INTO products (code, name, ingredients_text, pnns_group_1, created_at, last_modified_at) "
                "VALUES (:code, :name, :ingredients, 'unknown', :date, :date) "
                "ON CONFLICT (code) DO NOTHING RETURNING code"),
                {"code": code, "name": row["nom"] or None, "ingredients": row["ingredients"] or None,
                 "date": row["extrait_le"] or "2026-11-11"}).first()
            if inserted is None:            # déjà dans la base : on n'y touche pas
                continue
            added += 1
            values = {column: number(row[key]) for key, column in NUTRITION.items()}
            connection.execute(text(
                f"INSERT INTO nutrition (product_code, {', '.join(values)}) "
                f"VALUES (:code, {', '.join(':' + column for column in values)})"), {"code": code, **values})
            grade = (row["nutriscore"] or "").strip().lower()
            connection.execute(text(
                "INSERT INTO score (product_code, nutriscore_grade) VALUES (:code, :grade)"),
                {"code": code, "grade": grade if grade in ("a", "b", "c", "d", "e") else None})
            tags = {brand_tag(name) for name in (row["marque"] or "").split(",") if brand_tag(name)}
            for tag in sorted(tags):
                brand_id = connection.execute(text(
                    "INSERT INTO brands (name) VALUES (:tag) ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name "
                    "RETURNING id"), {"tag": tag}).scalar_one()
                connection.execute(text(
                    "INSERT INTO products_brands (product_code, brand_id) VALUES (:code, :id) ON CONFLICT DO NOTHING"),
                    {"code": code, "id": brand_id})
    return {"lus": len(rows), "ajoutes": added, "deja_presents": len(rows) - added}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ajoute le lot de l'atelier scanner au catalogue PostgreSQL.")
    parser.add_argument("chemin", nargs="?", default=str(DEFAULT_PATH), help="CSV du lot (défaut : %(default)s)")
    args = parser.parse_args(argv)
    counts = load_lot(Path(args.chemin))
    print(f"{counts['lus']} fiches lues : {counts['ajoutes']} ajoutées, {counts['deja_presents']} déjà présentes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
