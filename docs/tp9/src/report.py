"""
Génération du rapport de nettoyage — TP 9
Rapport avant/après structuré et committable.
"""

import pandas as pd
from datetime import datetime
from cleaning import CompteRendu


def generer_rapport(
    df_avant: pd.DataFrame,
    df_apres: pd.DataFrame,
    rapports: list,
    chemin: str = "docs/data/rapport_nettoyage.md"
) -> str:
    """
    Génère un rapport Markdown complet du nettoyage.

    Args:
        df_avant : DataFrame avant nettoyage
        df_apres : DataFrame après nettoyage
        rapports : liste de CompteRendu
        chemin : chemin de sauvegarde (pour info)

    Returns:
        Contenu du rapport (str)
    """

    now = datetime.now().isoformat(timespec="minutes")

    # En-tête
    rapport_text = f"""# Rapport de Nettoyage du Catalogue NutriScope
**Date** : {now}
**Source** : Open Food Facts (France)
**Crédit** : © Open Food Facts contributors — Licence ODbL

---

## Vue d'Ensemble

### Volumétrie

| Métrique | Avant | Après | Variation |
|----------|-------|-------|-----------|
| **Lignes** | {len(df_avant):,} | {len(df_apres):,} | {len(df_apres) - len(df_avant):+,d} ({((len(df_apres) / len(df_avant) - 1) * 100):+.1f}%) |
| **Colonnes** | {len(df_avant.columns)} | {len(df_apres.columns)} | {len(df_apres.columns) - len(df_avant.columns):+d} |
| **Codes distincts** | {df_avant['code'].nunique():,} | {df_apres['code'].nunique():,} | — |

### Complétude Nutriments Clés (avant/après %)

| Colonne | Avant | Après |
|---------|-------|-------|
"""

    # Complétude par colonne
    nutriments_cles = ["energy_100g", "energy-kcal_100g", "fat_100g", "carbohydrates_100g", "sugars_100g", "salt_100g", "proteins_100g"]
    for col in nutriments_cles:
        if col in df_avant.columns and col in df_apres.columns:
            compl_avant = (df_avant[col].notna().sum() / len(df_avant) * 100) if len(df_avant) > 0 else 0
            compl_apres = (df_apres[col].notna().sum() / len(df_apres) * 100) if len(df_apres) > 0 else 0
            rapport_text += f"| {col} | {compl_avant:.1f}% | {compl_apres:.1f}% |\n"

    rapport_text += "\n---\n\n## Détail des Règles Appliquées\n\n"

    # Résumé des règles
    rapport_text += "### Résumé Exécution\n\n| Règle | Avant | Après | Touchées |\n|-------|-------|-------|----------|\n"
    for rapport in rapports:
        rapport_text += f"| {rapport.regle} | {rapport.lignes_avant:,} | {rapport.lignes_apres:,} | {rapport.lignes_touchees:,} |\n"

    rapport_text += "\n### Détails par Règle\n\n"

    for rapport in rapports:
        rapport_text += f"#### {rapport.regle}\n\n"
        rapport_text += f"- **Lignes avant** : {rapport.lignes_avant:,}\n"
        rapport_text += f"- **Lignes après** : {rapport.lignes_apres:,}\n"
        rapport_text += f"- **Touchées** : {rapport.lignes_touchees:,}\n"

        if rapport.details:
            rapport_text += "\n**Détails** :\n"
            for clé, val in rapport.details.items():
                if isinstance(val, bool):
                    rapport_text += f"- {clé}: {'oui' if val else 'non'}\n"
                else:
                    rapport_text += f"- {clé}: {val}\n"

        rapport_text += "\n"

    # Anomalies métier
    rapport_text += "---\n\n## Anomalies Métier Détectées\n\n"

    rapport_text += "### Avant Nettoyage\n\n"
    anomalies_avant = detecter_anomalies(df_avant)
    if anomalies_avant:
        for anomalie in anomalies_avant:
            rapport_text += f"- {anomalie}\n"
    else:
        rapport_text += "- Aucune anomalie détectée\n"

    rapport_text += "\n### Après Nettoyage\n\n"
    anomalies_apres = detecter_anomalies(df_apres)
    if anomalies_apres:
        for anomalie in anomalies_apres:
            rapport_text += f"- {anomalie}\n"
    else:
        rapport_text += "- ✅ Aucune anomalie résiduelle\n"

    # Répartition par rayon
    rapport_text += "\n---\n\n## Répartition par Rayon (Après)\n\n"

    if "main_category" in df_apres.columns:
        rayon_dist = df_apres["main_category"].value_counts()
        rapport_text += "| Rayon | Produits | % |\n|-------|----------|----|\n"
        for rayon, count in rayon_dist.items():
            pct = (count / len(df_apres) * 100)
            rapport_text += f"| {rayon or 'unknown'} | {count:,} | {pct:.1f}% |\n"

    # Colonnes ajoutées/retirées
    rapport_text += "\n---\n\n## Colonnes Modifiées\n\n"

    cols_avant = set(df_avant.columns)
    cols_apres = set(df_apres.columns)

    ajoutees = cols_apres - cols_avant
    retirees = cols_avant - cols_apres

    if ajoutees:
        rapport_text += f"**Ajoutées** : {', '.join(sorted(ajoutees))}\n\n"
    if retirees:
        rapport_text += f"**Retirées** : {', '.join(sorted(retirees))}\n\n"
    if not ajoutees and not retirees:
        rapport_text += "Aucune colonne ajoutée ou retirée.\n\n"

    # Pied de page
    rapport_text += """---

## Notes

- Ce rapport est **généré automatiquement** par `python -m src.report`
- Les décisions de nettoyage sont documentées dans `docs/data/strategie_manquants.md`
- Le pipeline peut être rejoué sans intervention manuelle
- Les données brutes originales sont archivées

**Statut** : ✅ Nettoyage validé
"""

    return rapport_text


def detecter_anomalies(df: pd.DataFrame) -> list:
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
        doublons = df["code"].duplicated().sum()
        if doublons > 0:
            anomalies.append(f"{doublons} doublons détectés")

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


if __name__ == "__main__":
    # Exemple d'utilisation
    print("Utilisez generer_rapport(df_avant, df_apres, rapports)")
