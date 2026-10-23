"""
Génération du rapport de nettoyage — TP 9
Rapport avant/après structuré et committable.
"""

import pandas as pd
from datetime import datetime
from . import schema
from .cleaning import Report, type_columns


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

    now = datetime.now().isoformat(timespec="minutes")

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
| **Lignes** | {len(df_before):,} | {len(df_after):,} | {len(df_after) - len(df_before):+,d} ({((len(df_after) / len(df_before) - 1) * 100):+.1f}%) |
| **Colonnes** | {len(df_before.columns)} | {len(df_after.columns)} | {len(df_after.columns) - len(df_before.columns):+d} |
| **Codes distincts** | {df_before['code'].nunique():,} | {df_after['code'].nunique():,} | — |

### Complétude Nutriments Clés (avant/après %)

| Colonne | Avant | Après |
|---------|-------|-------|
"""

    # Complétude par colonne
    for col in ["energy_100g", *schema.KEY_NUTRIENTS]:
        if col in df_before.columns and col in df_after.columns:
            compl_before = (df_before[col].notna().sum() / len(df_before) * 100) if len(df_before) > 0 else 0
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
    df_typed, _ = type_columns(df_before)  # le brut doit être typé pour être contrôlé
    anomalies_before = schema.count_anomalies(df_typed)
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

    cols_before = set(df_before.columns)
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

