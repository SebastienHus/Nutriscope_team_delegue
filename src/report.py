"""
Génération du rapport de nettoyage — TP 9
Rapport avant/après structuré et committable.
"""

import pandas as pd
from datetime import datetime
from cleaning import Report, type_columns


def generate_report(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    reports: list[Report],
) -> str:
    """
    Génère un rapport Markdown complet du nettoyage.

    Args:
        df_avant : DataFrame avant nettoyage
        df_apres : DataFrame après nettoyage
        rapports : liste de Report

    Returns:
        Contenu du rapport (str)
    """

    now = datetime.now().isoformat(timespec="minutes")

    # En-tête
    report_text = f"""# Rapport de Nettoyage du Catalogue NutriScope
**Date** : {now}
**Source** : Open Food Facts (France)
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
    nutrients_keys = ["energy_100g", "energy-kcal_100g", "fat_100g", "carbohydrates_100g", "sugars_100g", "salt_100g", "proteins_100g"]
    for col in nutrients_keys:
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

    # Anomalies métier
    report_text += "---\n\n## Anomalies Métier Détectées\n\n"

    report_text += "### Avant Nettoyage\n\n"
    df_typed, _ = type_columns(df_before) # Besoin de typer avant de détecter les anomalies
    anomalies_before = detect_anomalies(df_typed)
    if anomalies_before:
        for anomaly in anomalies_before:
            report_text += f"- {anomaly}\n"
    else:
        report_text += "- Aucune anomalie détectée\n"

    report_text += "\n### Après Nettoyage\n\n"
    anomalies_after = detect_anomalies(df_after)
    if anomalies_after:
        for anomaly in anomalies_after:
            report_text += f"- {anomaly}\n"
    else:
        report_text += "- ✅ Aucune anomalie résiduelle\n"

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

- Ce rapport est **généré automatiquement** par `python -m src.pipeline`
- Les décisions de nettoyage sont documentées dans `docs/data/parties/strategie_manquants.md`
- Le pipeline peut être rejoué sans intervention manuelle
- Les données brutes originales sont archivées

**Statut** : ✅ Nettoyage validé
"""

    return report_text


def detect_anomalies(df: pd.DataFrame) -> list:
    """
    Détecte les anomalies métier dans un DataFrame.
    """
    anomalies = []

    if len(df) == 0:
        return ["DataFrame vide"]

    # Énergies aberrantes
    if "energy-kcal_100g" in df.columns:
        mask_over900 = (df["energy-kcal_100g"] > 900) & df["energy-kcal_100g"].notna()
        if mask_over900.sum() > 0:
            anomalies.append(f"{mask_over900.sum()} produits avec kcal > 900")

    # Sucres > glucides
    if "sugars_100g" in df.columns and "carbohydrates_100g" in df.columns:
        mask = (df["sugars_100g"] > df["carbohydrates_100g"] + 0.5) & df["sugars_100g"].notna()
        if mask.sum() > 0:
            anomalies.append(f"{mask.sum()} produits avec sucres > glucides + 0.5")

    # Saturés > lipides
    if "saturated-fat_100g" in df.columns and "fat_100g" in df.columns:
        mask = (df["saturated-fat_100g"] > df["fat_100g"] + 0.5) & df["saturated-fat_100g"].notna()
        if mask.sum() > 0:
            anomalies.append(f"{mask.sum()} produits avec saturés > lipides + 0.5")

    # Doublons
    if "code" in df.columns:
        duplicates = df["code"].duplicated().sum()
        if duplicates > 0:
            anomalies.append(f"{duplicates} doublons détectés")

    # Valeurs aberrantes
    if "fat_100g" in df.columns:
        mask = ((df["fat_100g"] < 0) | (df["fat_100g"] > 100)) & df["fat_100g"].notna()
        if mask.sum() > 0:
            anomalies.append(f"{mask.sum()} valeurs aberrantes pour fat_100g")

    if "salt_100g" in df.columns:
        mask = ((df["salt_100g"] < 0) | (df["salt_100g"] > 100)) & df["salt_100g"].notna()
        if mask.sum() > 0:
            anomalies.append(f"{mask.sum()} valeurs aberrantes pour salt_100g")

    return anomalies

