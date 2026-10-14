"""
Rapport de nettoyage pour un nettoyage en un bloc OU en lots.

Le `report.generate_report` du TP 9 a besoin du tableau brut complet en mémoire (et y écrit l'heure) :
incompatible avec le nettoyage par lots et avec l'idempotence. Ici, on additionne les comptes rendus
(`cleaning.Report`) de chaque lot, et l'heure va dans le manifeste, pas dans le rapport.
"""

from __future__ import annotations

from collections import OrderedDict


def merge_reports(batches: list[list]) -> list[dict]:
    """Additionne, règle par règle, les comptes rendus de plusieurs lots (même ordre de règles)."""
    merged: "OrderedDict[str, dict]" = OrderedDict()
    for reports in batches:
        for report in reports:
            entry = merged.setdefault(report.rule, {"rule": report.rule, "lines_before": 0, "lines_after": 0,
                                                    "lines_changed": 0, "details": {}})
            entry["lines_before"] += int(report.lines_before)
            entry["lines_after"] += int(report.lines_after)
            entry["lines_changed"] += int(report.lines_changed)
            for key, value in (report.details or {}).items():
                try:
                    entry["details"][key] = entry["details"].get(key, 0) + int(value)
                except (TypeError, ValueError):
                    entry["details"][key] = value
    return list(merged.values())


def markdown(settings, raw_name: str, raw_rows: int, clean_df, rules: list[dict], key_nutrients: list[str]) -> str:
    lines = [
        "# Rapport de nettoyage — NutriScope (TP 13)", "",
        f"- Date des données : {settings.run_date.isoformat()}",
        f"- Entrée : `{raw_name}`",
        f"- Mode : {'un seul bloc' if settings.batches <= 1 else f'{settings.batches} lots (répartition par hachage du code)'}",
        "- Règles : `src/cleaning.py` (TP 9), inchangées, dans l'ordre du TP 9",
        "- Crédit : © Open Food Facts contributors — ODbL", "",
        "## Volumétrie", "",
        "| Mesure | Valeur |", "|---|---|",
        f"| Lignes brutes | {raw_rows:,} |".replace(",", " "),
        f"| Lignes nettoyées | {len(clean_df):,} |".replace(",", " "),
        f"| Part conservée | {100 * len(clean_df) / raw_rows:.1f} % |" if raw_rows else "| Part conservée | — |",
        f"| Colonnes nettoyées | {len(clean_df.columns)} |", "",
        "## Règles appliquées (totaux sur tous les lots)", "",
        "| Ordre | Règle | Avant | Après | Lignes touchées |", "|---|---|---|---|---|",
    ]
    for number, rule in enumerate(rules, 1):
        lines.append(f"| {number} | {rule['rule']} | {rule['lines_before']:,} | {rule['lines_after']:,} | "
                     f"{rule['lines_changed']:,} |".replace(",", " "))
    lines += ["", "## Détails par règle", ""]
    for rule in rules:
        if rule["details"]:
            lines.append(f"- **{rule['rule']}** : " + ", ".join(f"{k} = {v}" for k, v in rule["details"].items()))
    present = [c for c in key_nutrients if c in clean_df.columns]
    if present and len(clean_df):
        lines += ["", "## Complétude des nutriments clés après nettoyage", "", "| Colonne | Renseignée |", "|---|---|"]
        for column in present:
            lines.append(f"| {column} | {100 * clean_df[column].notna().mean():.1f} % |")
    lines += ["", "Données : © Open Food Facts contributors — ODbL.", ""]
    return "\n".join(lines)
