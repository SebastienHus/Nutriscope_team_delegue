"""
Pipeline complet — TP 9.

Exécution de bout en bout : lecture → nettoyage → rapport → export → base (optionnelle).

    python src/pipeline.py                                   # échantillon, sans base
    python src/pipeline.py data/en.openfoodfacts.org.products.csv -s "\\t" --load-db
"""

import argparse
import getpass
import os
import sys
import traceback
from pathlib import Path

from cleaning import DEFAULT_STRATEGY, clean
from create_database import init_database, load_products
from options import CONFIG, DATA_PATH
from reader import read_products, CHUNKSIZE
from report import generate_report

STEPS = 5


def step(number: int, title: str) -> None:
    print(f"\n[{number}/{STEPS}] {title}")


def main(csv_in: os.PathLike, csv_out: os.PathLike | None, report_path: os.PathLike,
         sep: str = ",", database: dict | None = None, chunksize: int=CHUNKSIZE) -> int:
    """
    Pipeline complet.

    Args:
        csv_in : export Open Food Facts brut
        csv_out : CSV nettoyé (par défaut `data/clean/<nom du fichier d'entrée>`)
        report_path : rapport Markdown
        sep : séparateur de l'export brut (le CSV nettoyé utilise la virgule)
        database : identifiants PostgreSQL (`username`, `password`, `host`, `port`) ;
            `None` pour ne pas charger la base

    Retourne 0 si tout s'est bien passé, 1 sinon.
    """
    csv_in = Path(csv_in)
    csv_out = DATA_PATH / "clean" / csv_in.name if csv_out is None else Path(csv_out)
    report_path = Path(report_path)

    print("=" * 80)
    print("PIPELINE NETTOYAGE — NutriScope TP 9")
    print("=" * 80)

    step(1, f"Lecture de {csv_in}...")
    try:
        df_raw = read_products(csv_in, CONFIG["columns"], sep=sep, chunksize=chunksize)
        print(f"  ✓ {len(df_raw):,} lignes, {len(df_raw.columns)} colonnes")
    except FileNotFoundError:
        print(f"  ✗ Fichier introuvable : {csv_in}")
        return 1

    step(2, "Nettoyage...")
    try:
        df_clean, reports = clean(df_raw, DEFAULT_STRATEGY)
    except ValueError as error:
        print(f"  ✗ {error}")
        return 1
    for report in reports:
        status = "✓" if report.lines_changed == 0 else "○"
        print(f"    {status} {report}")
    print(f"  ✓ {len(df_clean):,} lignes conservées ({len(df_clean) / len(df_raw):.1%}), schéma respecté")

    step(3, "Rapport...")
    report_text = generate_report(df_raw, df_clean, reports, source=csv_in.name)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    print(f"  ✓ {report_path}")

    step(4, "Export du CSV nettoyé...")
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(csv_out, index=False)
    print(f"  ✓ {csv_out}")

    step(5, "Chargement de la base...")
    if database is None:
        print("  - ignoré (option --load-db absente)")
    else:
        try:
            engine = init_database(CONFIG, **database)
            for table, count in load_products(engine, df_clean).items():
                print(f"    {table}: {count:,} lignes")
        except Exception:
            traceback.print_exc()
            return 1

    print("\n" + "=" * 80)
    print("✅ PIPELINE TERMINÉ")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nettoyage de l'export Open Food Facts et chargement de la base.")
    parser.add_argument("csv_in", nargs="?", default="./data-nutriscope/echantillon_france.csv",
                        help="Chemin du fichier CSV d'entrée")
    parser.add_argument("csv_out", nargs="?", default=None, help="Chemin du fichier CSV de sortie")
    parser.add_argument("report_path", nargs="?", default="./data/docs/rapport_nettoyage.md",
                        help="Chemin du rapport Markdown")
    parser.add_argument("-s", "--separator", default=",",
                        help="Séparateur du CSV à lire. Le CSV de sortie utilise la virgule.")
    parser.add_argument("--load-db", action="store_true", help="Recrée et charge la base PostgreSQL")
    parser.add_argument("-u", "--username", default="postgres")
    parser.add_argument("-pwd", "--password", default=None,
                        help="Mot de passe ; demandé de façon masquée s'il est omis")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--chunksize", type=int, default=CHUNKSIZE)
    args = parser.parse_args()

    # Traite les caractères d'échappement (ex. "\t")
    separator = args.separator.encode().decode("unicode-escape")
    database = None
    if args.load_db:
        database = {
            "username": args.username,
            "password": args.password or getpass.getpass("Mot de passe PostgreSQL : "),
            "host": args.host,
            "port": args.port,
        }
    sys.exit(main(args.csv_in, args.csv_out, args.report_path, sep=separator, database=database))
