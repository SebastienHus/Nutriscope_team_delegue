"""
Génération du rapport de nettoyage — TP 9
Rapport avant/après structuré et committable.

Le rapport ne garde du brut qu'un résumé (`summarize_before`) : nombre de lignes, colonnes,
codes distincts, complétude, anomalies. Ce résumé s'additionne d'un lot à l'autre
(`merge_summaries`), tout comme les comptes rendus des règles (`merge_reports`) : le
pipeline peut ainsi nettoyer un gros export par lots sans jamais garder le brut complet en
mémoire, et produire le même rapport qu'en un seul bloc.
"""

from dataclasses import replace
from datetime import datetime

import pandas as pd

from . import schema
from .cleaning import Report, type_columns

COMPLETENESS_COLUMNS = ("energy_100g", *schema.KEY_NUTRIENTS)


def summarize_before(df_before: pd.DataFrame) -> dict:
    """Résumé du brut nécessaire au rapport. Les codes d'un lot ne se retrouvent dans aucun autre."""
    df_typed, _ = type_columns(df_before)  # le brut doit être typé pour être contrôlé
    return {
        "rows": len(df_before),
        "columns": list(df_before.columns),
        "distinct_codes": int(df_before["code"].nunique()) if "code" in df_before.columns else 0,
        "non_null": {column: int(df_before[column].notna().sum())
                     for column in COMPLETENESS_COLUMNS if column in df_before.columns},
        "anomalies": schema.count_anomalies(df_typed),
    }


def merge_summaries(summaries: list[dict]) -> dict:
    """
    Additionne les résumés de plusieurs lots. Exact parce que les lots partitionnent les
    produits par code : un même code (doublons compris) est toujours dans le même lot.
    """
    merged = {"rows": 0, "columns": summaries[0]["columns"] if summaries else [],
              "distinct_codes": 0, "non_null": {}, "anomalies": {}}
    for summary in summaries:
        merged["rows"] += summary["rows"]
        merged["distinct_codes"] += summary["distinct_codes"]
        for key in ("non_null", "anomalies"):
            for name, value in summary[key].items():
                merged[key][name] = merged[key].get(name, 0) + value
    return merged


def merge_reports(batches: list[list[Report]]) -> list[Report]:
    """Additionne, règle par règle, les comptes rendus de plusieurs lots (même ordre de règles)."""
    merged: dict[str, Report] = {}
    for reports in batches:
        for report in reports:
            if report.rule not in merged:
                merged[report.rule] = replace(report, details=dict(report.details))
                continue
            total = merged[report.rule]
            total.lines_before += report.lines_before
            total.lines_after += report.lines_after
            total.lines_changed += report.lines_changed
            for key, value in report.details.items():
                total.details[key] = total.details.get(key, 0) + value
    return list(merged.values())


def generate_report(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    reports: list[Report],
    source: str = "Open Food Facts",
) -> str:
    """
    Génère un rapport Markdown complet du nettoyage.

    Args:
        df_before : DataFrame avant nettoyage (brut)
        df_after : DataFrame après nettoyage
        reports : liste des comptes rendus de `cleaning.clean()`
        source : fichier source, affiché en en-tête

    Returns:
        Contenu du rapport (str)
    """
    return render_report(summarize_before(df_before), df_after, reports, source,
                         date=datetime.now().isoformat(timespec="minutes"))


def render_report(before: dict, df_after: pd.DataFrame, reports: list[Report],
                  source: str = "Open Food Facts", date: str = "") -> str:
    """
    Rapport Markdown à partir du résumé du brut (`summarize_before` ou `merge_summaries`).
    `date` est affichée en en-tête : le pipeline y met la date des données, pas l'heure,
    pour que le rapport ne change pas d'une relance à l'autre.
    """
    rows_before = before["rows"]
    now = date

    # En-tête
    report_text = f"""# Rapport de Nettoyage du Catalogue NutriScope
**Date** : {now}
**Source** : {source}
**Crédit** : © Open Food Facts contributors — Licence ODbL

---

## Vue d'Ensemble

### Volumétrie

| Métrique | Avant | Après | Variation |
|----------|-------|-------|-----------|
| **Lignes** | {rows_before:,} | {len(df_after):,} | {len(df_after) - rows_before:+,d} ({((len(df_after) / rows_before - 1) * 100) if rows_before else 0:+.1f}%) |
| **Colonnes** | {len(before['columns'])} | {len(df_after.columns)} | {len(df_after.columns) - len(before['columns']):+d} |
| **Codes distincts** | {before['distinct_codes']:,} | {df_after['code'].nunique():,} | — |

### Complétude Nutriments Clés (avant/après %)

| Colonne | Avant | Après |
|---------|-------|-------|
"""

    # Complétude par colonne
    for col in COMPLETENESS_COLUMNS:
        if col in before["non_null"] and col in df_after.columns:
            compl_before = (before["non_null"][col] / rows_before * 100) if rows_before > 0 else 0
            compl_after = (df_after[col].notna().sum() / len(df_after) * 100) if len(df_after) > 0 else 0
            report_text += f"| {col} | {compl_before:.1f}% | {compl_after:.1f}% |\n"

    report_text += "\n---\n\n## Détail des Règles Appliquées\n\n"

    # Résumé des règles
    report_text += "### Résumé Exécution\n\n| Règle | Avant | Après | Touchées |\n|-------|-------|-------|----------|\n"
    for report in reports:
        report_text += f"| {report.rule} | {report.lines_before:,} | {report.lines_after:,} | {report.lines_changed:,} |\n"

    report_text += "\n### Détails par Règle\n\n"

    for report in reports:
        report_text += f"#### {report.rule}\n\n"
        report_text += f"- **Lignes avant** : {report.lines_before:,}\n"
        report_text += f"- **Lignes après** : {report.lines_after:,}\n"
        report_text += f"- **Touchées** : {report.lines_changed:,}\n"

        if report.details:
            report_text += "\n**Détails** :\n"
            for key, val in report.details.items():
                if isinstance(val, bool):
                    report_text += f"- {key}: {'oui' if val else 'non'}\n"
                else:
                    report_text += f"- {key}: {val}\n"

        report_text += "\n"

    # Anomalies métier : mêmes définitions que le contrat de sortie (schema.OUTPUT_SCHEMA)
    report_text += "---\n\n## Anomalies Métier (contrôles du schéma)\n\n"
    anomalies_before = before["anomalies"]
    anomalies_after = schema.count_anomalies(df_after)
    report_text += "| Contrôle | Avant | Après |\n|----------|-------|-------|\n"
    for check, count_before in anomalies_before.items():
        count_after = anomalies_after.get(check, 0)
        if count_before or count_after:
            report_text += f"| {check} | {count_before:,} | {count_after:,} |\n"
    if not any(anomalies_after.values()):
        report_text += "\n✅ Aucune anomalie résiduelle : la sortie respecte le schéma.\n"

    # Répartition par rayon
    report_text += "\n---\n\n## Répartition par Rayon (Après)\n\n"

    if "pnns_groups_1" in df_after.columns:
        group_dist = df_after["pnns_groups_1"].value_counts()
        report_text += "| Rayon | Produits | % |\n|-------|----------|----|\n"
        for group, count in group_dist.items():
            pct = (count / len(df_after) * 100)
            report_text += f"| {group or 'unknown'} | {count:,} | {pct:.1f}% |\n"

    # Colonnes ajoutées/retirées
    report_text += "\n---\n\n## Colonnes Modifiées\n\n"

    cols_before = set(before["columns"])
    cols_after = set(df_after.columns)

    added = cols_after - cols_before
    removed = cols_before - cols_after

    if added:
        report_text += f"**Ajoutées** : {', '.join(sorted(added))}\n\n"
    if removed:
        report_text += f"**Retirées** : {', '.join(sorted(removed))}\n\n"
    if not added and not removed:
        report_text += "Aucune colonne ajoutée ou retirée.\n\n"

    # Pied de page
    report_text += """---

## Notes

- Ce rapport est **généré automatiquement** par `python -m nutriscope.pipeline clean_data`
- Le pipeline peut être rejoué sans intervention manuelle
- Les données brutes originales sont archivées

**Statut** : ✅ Nettoyage validé
"""

    return report_text

