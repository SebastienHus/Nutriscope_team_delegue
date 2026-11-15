"""Mesure de votre scanner sur le lot de 22 photos.

Le script appelle votre fonction ``scan_label(image)`` sur chaque photo d'étiquette,
puis compare son résultat à ``data/verite_terrain.csv``. Il ne contient aucune partie du scanner.

Lancement, depuis la racine de votre dépôt (``tools/`` et ``data/`` côte à côte) :

    python tools/measure_scanner.py --version palier1
    python tools/measure_scanner.py --version palier1 --ids 02 10 21      # 3 photos seulement
    python tools/measure_scanner.py --version vote3 --scanner src/workflow.py:scan_label
    python tools/measure_scanner.py --history                             # revoir le tableau des versions

Pour chaque photo et chaque nutriment, la valeur rendue tombe dans une case :

- correct   : la bonne valeur (aux arrondis près), ou null quand l'étiquette n'en donne pas ;
- wrong     : une valeur, mais pas la bonne ;
- invented  : une valeur alors que l'étiquette n'en donne pas (le cas le plus grave) ;
- missed    : null alors que l'étiquette donne une valeur ;
- no_result : le scanner a levé une exception ou n'a pas rendu de dictionnaire.

Sorties, dans ``results/`` :

- ``<version>.csv`` : une ligne par photo, avec le détail des erreurs ;
- ``history.csv`` : une ligne par passage ; la première version est votre référence.
"""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from scan_tools.scan_common import (DEFAULT_SCANNER, NUTRIENTS, STATUSES, ScannerNotFound, contract_problems,
                             is_number, load_ground_truth, load_scanner, photo)

OUTCOMES = ("correct", "wrong", "invented", "missed")


# --- Comparaison d'un résultat avec la vérité terrain ---

def same_value(read: float, expected: float) -> bool:
    """Tolérance d'arrondi : 0,49 et 0,5 diffèrent, 467 et 467,0 non."""
    return abs(read - expected) <= 0.011 + 0.005 * abs(expected)


def outcome(read: Any, expected: float | None) -> str:
    if expected is None:
        return "correct" if read is None else "invented"
    if read is None:
        return "missed"
    return "correct" if is_number(read) and same_value(float(read), expected) else "wrong"


def words(text: str) -> set[str]:
    no_accents = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return set("".join(c if c.isalnum() else " " for c in no_accents).split())


def name_matches(read: Any, expected: str) -> bool:
    """Juste si tous les mots de l'un se retrouvent dans l'autre (casse et accents ignorés)."""
    if not isinstance(read, str) or not read.strip():
        return False
    a, b = words(read), words(expected)
    return bool(a) and (a <= b or b <= a)


def compare(result: Any, product: dict[str, Any], latency: float, error: str | None) -> dict[str, Any]:
    row: dict[str, Any] = {"id": product["id"], "product": product["nom"]}
    if not error and not isinstance(result, dict):
        error = f"le scanner a rendu {type(result).__name__}, pas un dictionnaire"
    r = result if isinstance(result, dict) else {}
    nutrients = r.get("nutriments") if isinstance(r.get("nutriments"), dict) else {}
    row["status"] = "EXCEPTION" if error else str(r.get("statut"))
    details = []
    for k in NUTRIENTS:
        read, expected = nutrients.get(k), product["nutriments"][k]
        row[k] = "no_result" if error else outcome(read, expected)   # aucune case « correct » sans résultat
        if row[k] != "correct":
            details.append(f"{k}: lu {read if read is not None else 'null'} / attendu {expected if expected is not None else 'null'}")
    for o in OUTCOMES:
        row[o] = sum(row[k] == o for k in NUTRIENTS)
    p = r.get("produit") if isinstance(r.get("produit"), dict) else {}
    row["name_correct"] = name_matches(p.get("nom"), product["nom"])
    row["base_correct"] = r.get("base") == product["base"]
    read_less_than = set(r.get("inferieur_a") or []) if isinstance(r.get("inferieur_a"), list) else set()
    row["less_than_correct"] = read_less_than == set(product["inferieur_a"])
    metrics = r.get("mesures") if isinstance(r.get("mesures"), dict) else {}
    row["latency_s"] = round(latency, 2)
    for k, column in (("appels_modele", "model_calls"), ("tokens_entree", "input_tokens"),
                      ("tokens_sortie", "output_tokens")):
        row[column] = metrics.get(k) if is_number(metrics.get(k)) else None
    row["alerts"] = len(r.get("alertes") or []) if isinstance(r.get("alertes"), list) else 0
    contract = [] if error else contract_problems(result)
    row["contract_violations"] = " | ".join(contract)
    row["errors"] = error or " ; ".join(details)
    return row


# --- Affichage ---

def table(headers: list[str], rows: list[list[Any]]) -> str:
    texts = [[str(c) for c in r] for r in [headers, *rows]]
    widths = [max(len(r[i]) for r in texts) for i in range(len(headers))]

    def line(r: list[str]) -> str:
        return "  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip()

    return "\n".join([line(texts[0]), "  ".join("-" * w for w in widths), *map(line, texts[1:])])


def pct(n: int, total: int) -> str:
    return f"{100 * n / total:.0f} %" if total else "-"


def mean(values: list[Any]) -> float | None:
    v = [x for x in values if x is not None]
    return statistics.mean(v) if v else None


def show(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    print("\nPar photo")
    print(table(["id", "produit", "statut", "justes/9", "inventées", "manquées", "fausses", "latence s", "alertes"],
                [[r["id"], r["product"][:30], r["status"], r["correct"], r["invented"], r["missed"], r["wrong"],
                  f"{r['latency_s']:.1f}", r["alerts"]] for r in rows]))
    n = len(rows)
    print("\nPar champ")
    lines = [[k, sum(r[k] == "correct" for r in rows), sum(r[k] == "wrong" for r in rows),
              sum(r[k] == "invented" for r in rows), sum(r[k] == "missed" for r in rows),
              pct(sum(r[k] == "correct" for r in rows), n)] for k in NUTRIENTS]
    lines += [[field, sum(r[key] for r in rows), n - sum(r[key] for r in rows), "", "", pct(sum(r[key] for r in rows), n)]
              for field, key in (("nom", "name_correct"), ("base", "base_correct"), ("inferieur_a", "less_than_correct"))]
    print(table(["champ", "justes", "fausses", "inventées", "manquées", "justesse"], lines))
    print(f"\nGlobal ({n} photos, {n * len(NUTRIENTS)} valeurs de nutriments)")
    print(f"  justesse des nutriments : {summary['accuracy']}")
    print(f"  valeurs inventées : {summary['invented']}   manquées : {summary['missed']}   fausses : {summary['wrong']}")
    print(f"  statuts : " + "   ".join(f"{s} {summary[s]}" for s in STATUSES)
          + f"   exceptions {summary['exceptions']}   hors contrat {summary['contract_violations']}")
    print(f"  latence : moyenne {summary['latency_mean_s']} s, max {summary['latency_max_s']} s")
    print(f"  par photo : {summary['calls_per_photo']} appel(s) au modèle, {summary['input_tokens_per_photo']} tokens "
          f"en entrée, {summary['output_tokens_per_photo']} en sortie, coût {summary['cost_per_photo_usd']} $")
    for r in rows:
        if r["status"] == "EXCEPTION":
            print(f"  ✗ photo {r['id']} : exception — {r['errors']}")
        elif r["contract_violations"]:
            print(f"  ✗ photo {r['id']} hors contrat : {r['contract_violations']}")


def show_history(path: Path) -> None:
    if not path.exists():
        print(f"Pas encore d'historique ({path}).")
        return
    with open(path, encoding="utf-8") as f:
        versions = list(csv.DictReader(f))
    if not versions:
        return
    ref = versions[0]
    lines = []
    for v in versions:
        delta = float(v["accuracy"].rstrip(" %")) - float(ref["accuracy"].rstrip(" %"))
        delta_text = f"{delta:+.0f} pts" if v["ids"] == ref["ids"] else "autres photos"
        lines.append([v["version"], v["photos"], v["accuracy"], delta_text, v["invented"],
                      v["missed"], v["exceptions"], v["latency_mean_s"], v["input_tokens_per_photo"],
                      v["cost_per_photo_usd"]])
    print(f"\nHistorique des versions (référence : {ref['version']})")
    print(table(["version", "photos", "justesse", "écart / réf.", "inventées", "manquées", "exceptions",
                 "latence s", "tokens entrée", "coût $"], lines))
    print("Comparez seulement des versions passées sur les mêmes photos.")


# --- Programme ---

def summarize(rows: list[dict[str, Any]], input_price: float, output_price: float, version: str,
              ids: list[str] | None) -> dict[str, Any]:
    total = len(rows) * len(NUTRIENTS)
    tin, tout = mean([r["input_tokens"] for r in rows]), mean([r["output_tokens"] for r in rows])
    cost = (tin or 0) * input_price / 1e6 + (tout or 0) * output_price / 1e6
    calls = mean([r["model_calls"] for r in rows])
    return {
        "version": version, "date": datetime.now().strftime("%Y-%m-%d %H:%M"), "photos": len(rows),
        "ids": " ".join(ids) if ids else "all",
        "accuracy": pct(sum(r["correct"] for r in rows), total),
        "invented": sum(r["invented"] for r in rows), "missed": sum(r["missed"] for r in rows),
        "wrong": sum(r["wrong"] for r in rows),
        "names_correct": sum(r["name_correct"] for r in rows), "bases_correct": sum(r["base_correct"] for r in rows),
        "exceptions": sum(r["status"] == "EXCEPTION" for r in rows),
        "contract_violations": sum(bool(r["contract_violations"]) for r in rows),
        **{s: sum(r["status"] == s for r in rows) for s in STATUSES},
        "latency_mean_s": round(statistics.mean(r["latency_s"] for r in rows), 2),
        "latency_max_s": round(max(r["latency_s"] for r in rows), 2),
        "calls_per_photo": "?" if calls is None else round(calls, 1),
        "input_tokens_per_photo": "?" if tin is None else round(tin),
        "output_tokens_per_photo": "?" if tout is None else round(tout),
        "cost_per_photo_usd": round(cost, 5),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists() or not append
    with open(path, "a" if append else "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        if new:
            writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    # Console Windows en cp1252 (sortie redirigée) : un caractère comme ✗ ne doit pas faire planter.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    p = argparse.ArgumentParser(description="Mesure de scan_label sur le lot de 22 photos.")
    p.add_argument("--version", help="nom de la version mesurée (palier1, validation, vote3…)")
    p.add_argument("--scanner", default=DEFAULT_SCANNER,
                   help=f"où est votre fonction : fichier.py:nom_fonction (défaut : {DEFAULT_SCANNER})")
    p.add_argument("--ids", nargs="+", help="numéros des photos à passer (ex. 02 10 21) ; défaut : les 22")
    p.add_argument("--photo", choices=("etiquette", "face"), default="etiquette", help="photo envoyée (défaut : etiquette)")
    p.add_argument("--input-price", type=float, default=0.0, help="$ par million de tokens en entrée (0 en local)")
    p.add_argument("--output-price", type=float, default=0.0, help="$ par million de tokens en sortie (0 en local)")
    p.add_argument("--results", default="results", help="dossier des sorties (défaut : results/)")
    p.add_argument("--history", action="store_true", help="afficher seulement le tableau des versions")
    a = p.parse_args(argv)
    folder = Path(a.results)
    if a.history:
        show_history(folder / "history.csv")
        return 0
    if not a.version:
        p.error("donnez un nom à la version mesurée : --version palier1")

    try:
        scan_label = load_scanner(a.scanner)
    except ScannerNotFound as e:
        print(f"✗ Scanner introuvable : {e}", file=sys.stderr)
        return 2

    products = load_ground_truth()
    if a.ids:
        unknown = set(a.ids) - {prod["id"] for prod in products}
        if unknown:
            p.error(f"photos inconnues : {' '.join(sorted(unknown))} (numéros de 01 à 22)")
        products = [prod for prod in products if prod["id"] in a.ids]

    rows = []
    for product in products:
        print(f"photo {product['id']} ({product['nom'][:40]})…", end=" ", flush=True)
        start, error, result = time.perf_counter(), None, None
        try:
            result = scan_label(str(photo(product, a.photo)))
        except Exception as e:  # le contrat l'interdit : on le compte, on continue
            error = f"{type(e).__name__}: {e}"
        latency = time.perf_counter() - start
        rows.append(compare(result, product, latency, error))
        print(f"{rows[-1]['status']}, {rows[-1]['correct']}/9 justes, {latency:.1f} s")

    summary = summarize(rows, a.input_price, a.output_price, a.version, a.ids)
    show(rows, summary)
    file_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in a.version)
    write_csv(folder / f"{file_name}.csv", rows)
    write_csv(folder / "history.csv", [summary], append=True)
    show_history(folder / "history.csv")
    print(f"\nDétail par photo : {folder / (file_name + '.csv')}")
    return 1 if summary["exceptions"] or summary["contract_violations"] else 0


if __name__ == "__main__":
    sys.exit(main())
