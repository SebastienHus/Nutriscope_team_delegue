"""
Point d'entrée unique du pipeline NutriScope (TP 13).

    python -m nutriscope.pipeline all                     # les 5 étapes, du CSV brut aux exports
    python -m nutriscope.pipeline nettoyer                # une étape seule (elle retrouve son entrée)
    python -m nutriscope.pipeline all --skip charger_base # sans PostgreSQL
    python -m nutriscope.pipeline all --source "C:/…/en.openfoodfacts.org.products.csv"   # extrait complet
    python -m nutriscope.pipeline exports --date 20261014 --force                         # rejouer une date
    python -m nutriscope.pipeline status                  # dernières sorties et dernières durées
    python -m nutriscope.pipeline clean                   # efface les sorties (sauf exports figés)

Le Makefile n'est qu'une façade sur cette CLI : la logique ne vit qu'ici.
Toutes les options ont un équivalent en variable d'environnement (voir nutriscope/config.py).

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import argparse
import sys

from nutriscope import __version__, journal
from nutriscope.config import STEP_NAMES, Settings, parse_date
from nutriscope.files import dated, rel, remove
from nutriscope.steps import charger, charger_base, exports, nettoyer, parquet
from nutriscope.steps.base import run_step, skipped

STEPS = {
    "charger": charger.run,
    "nettoyer": nettoyer.run,
    "charger_base": charger_base.run,
    "parquet": parquet.run,
    "exports": exports.run,
}
ICONS = {"ok": "OK  ", "skipped": "SAUT", "failed": "ÉCHEC"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m nutriscope.pipeline",
                                description="Pipeline NutriScope : du CSV Open Food Facts brut aux données prêtes pour le ML.")
    p.add_argument("command", choices=[*STEP_NAMES, "all", "status", "clean"],
                   help="une étape, « all » (les 5 dans l'ordre), « status » ou « clean »")
    p.add_argument("--source", help="CSV ou Parquet source (défaut : échantillon data-nutriscope/echantillon_france.csv)")
    p.add_argument("--sep", help="séparateur de la source (défaut : détecté ; \\t pour l'export complet)")
    p.add_argument("--date", help="date des sorties AAAAMMJJ (défaut : aujourd'hui, Europe/Paris)")
    p.add_argument("--data-dir", help="dossier des sorties (défaut : data/)")
    p.add_argument("--batches", type=int, help="lots du nettoyage (défaut 8 ; 1 = un seul bloc)")
    p.add_argument("--memory", help="plafond mémoire DuckDB, ex. 12GB")
    p.add_argument("--skip", action="append", choices=STEP_NAMES, default=[],
                   help="étape à sauter dans « all » (répétable), ex. --skip charger_base")
    p.add_argument("--force", action="store_true", help="réécrire l'export figé du jour (étape exports)")
    p.add_argument("--include-exports", action="store_true", help="avec « clean » : effacer aussi les exports figés")
    p.add_argument("--verbose", action="store_true", help="afficher la trace Python complète en cas d'erreur imprévue")
    return p


def print_header(settings, command: str) -> None:
    print("=" * 78)
    print(f"NutriScope pipeline {__version__} — {command}")
    print(f"  date      : {settings.run_date.isoformat()}")
    print(f"  source    : {rel(settings.source)}")
    print(f"  sorties   : {rel(settings.data_dir)}")
    print(f"  nettoyage : {settings.batches} lot(s) | DuckDB : {settings.duckdb_memory}")
    print("=" * 78)


def print_result(result) -> None:
    rows = "" if result.rows is None else f"{result.rows:>10,} lignes".replace(",", " ")
    print(f"[{ICONS.get(result.status, result.status)}] {result.step:<13} {result.seconds:8.1f} s {rows}  {result.message}")


def run(settings, names: list[str], force: bool, verbose: bool) -> int:
    results = []
    for name in names:
        if name in settings.skip:
            result = skipped(name, settings, "ignorée à la demande (--skip / NUTRISCOPE_SKIP)")
        else:
            print(f"--> {name} …", flush=True)
            result = run_step(name, STEPS[name], settings, force=force, verbose=verbose)
        print_result(result)
        results.append(result)
        if result.status == "failed":
            break
    print("-" * 78)
    total = sum(r.seconds for r in results)
    failed = [r for r in results if r.status == "failed"]
    print(f"Durée totale : {total:.1f} s — journal : {rel(journal.journal_path(settings))}")
    if failed:
        print(f"ÉCHEC à l'étape « {failed[0].step} » : {failed[0].message}")
        return 1
    print("Terminé sans erreur.")
    return 0


def status(settings) -> int:
    patterns = [("charger", settings.raw_dir, charger.PREFIX, ".parquet"),
                ("nettoyer", settings.clean_dir, nettoyer.PREFIX, ".parquet"),
                ("charger_base", settings.db_dir, "base_", ".json"),
                ("parquet", settings.parquet_dir, parquet.PREFIX, ""),
                ("exports", settings.exports_dir, exports.PREFIX, ".parquet")]
    print("Dernières sorties :")
    for name, directory, prefix, suffix in patterns:
        found = dated(directory, prefix, suffix)
        print(f"  {name:<13} {rel(found[-1][1]) if found else '— aucune —'}")
    lines = journal.read(settings)
    if lines:
        print("Dernières lignes du journal :")
        for line in lines[-10:]:
            print(f"  {line['timestamp']}  {line['step']:<13} {line['status']:<8} {line['seconds']:>8} s  "
                  f"{line['rows'] if line['rows'] is not None else ''}")
    return 0


def clean(settings, include_exports: bool) -> int:
    targets = [settings.raw_dir, settings.clean_dir, settings.db_dir, settings.parquet_dir, settings.tmp_dir]
    if include_exports:
        targets.append(settings.exports_dir)
    for target in targets:
        if target.exists():
            remove(target, settings.data_dir)
            print(f"effacé : {rel(target)}")
    if not include_exports:
        print("exports figés conservés (ajoutez --include-exports pour les effacer)")
    print("La base PostgreSQL n'est pas touchée : elle est recréée par l'étape charger_base.")
    return 0


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):           # accents et symboles lisibles sous Windows
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    overrides = dict(source=args.source, sep=args.sep, data_dir=args.data_dir, batches=args.batches,
                     duckdb_memory=args.memory, run_date=parse_date(args.date) if args.date else None)
    settings = Settings.from_env(**overrides)
    if args.command == "status":
        return status(settings)
    if args.command == "clean":
        return clean(settings, args.include_exports)
    if args.command == "all":
        names = list(STEP_NAMES)
        settings = Settings.from_env(**overrides, skip=tuple(dict.fromkeys([*settings.skip, *args.skip])))
    else:                                   # une étape demandée explicitement n'est jamais sautée
        names = [args.command]
        settings = Settings.from_env(**overrides, skip=())
    print_header(settings, args.command)
    return run(settings, names, force=args.force, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
