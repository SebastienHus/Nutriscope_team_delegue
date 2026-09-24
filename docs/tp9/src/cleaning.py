"""
Nettoyage industrialisé du catalogue NutriScope — TP 9
Module de nettoyage des données Open Food Facts avec règles pures et rejouables.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Tuple
from datetime import datetime

# ============================================================================
# CONTRAT COMMUN
# ============================================================================

@dataclass
class CompteRendu:
    """Rapport d'exécution d'une règle de nettoyage."""
    regle: str
    lignes_avant: int
    lignes_apres: int
    lignes_touchees: int
    details: dict = field(default_factory=dict)

    def __str__(self):
        return (
            f"{self.regle}: {self.lignes_touchees} lignes touchées "
            f"({self.lignes_avant} → {self.lignes_apres})"
        )


# ============================================================================
# CONSTANTES MÉTIER
# ============================================================================

KCAL_MAX = 900.0
KCAL_MIN = 0.0
KJ_PAR_KCAL = 4.184
SEL_PAR_SODIUM = 2.5
ENERGIE_ABERRANTE_MAX = 3000.0  # kJ très aberrant

NUTRIMENTS_BORNES = {
    "fat_100g": (0, 100),
    "saturated-fat_100g": (0, 100),
    "carbohydrates_100g": (0, 100),
    "sugars_100g": (0, 100),
    "fiber_100g": (0, 100),
    "proteins_100g": (0, 100),
    "salt_100g": (0, 100),
    "sodium_100g": (0, 100),
    "energy-kcal_100g": (0, 900),
    "energy_100g": (0, 3500),  # kJ (900 kcal ≈ 3765 kJ)
}

SEUIL_COMPLETUDE = 0.5  # 50% de complétude minimal pour nutriments clés
NUTRIMENTS_CLES = ["energy_100g", "energy-kcal_100g", "fat_100g", "sugars_100g", "salt_100g"]

RAYONS_EXCLUS = ["unknown", "no-category", ""]


# ============================================================================
# RÈGLE 1 : TYPAGE DES COLONNES
# ============================================================================

def typer_colonnes(df: pd.DataFrame) -> Tuple[pd.DataFrame, CompteRendu]:
    """
    Typage cohérent des colonnes.
    - code : string (code-barres)
    - compteurs numériques : Int64 (nullable)
    - nutriments : float64
    """
    df = df.copy()

    # Codes-barres en string
    if "code" in df.columns:
        df["code"] = df["code"].astype(str)

    # Nutriments en float64
    cols_nutriments = [c for c in df.columns if any(x in c for x in ["energy", "fat", "carb", "sugars", "fiber", "proteins", "salt", "sodium"])]
    for col in cols_nutriments:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float64")

    # Scores / indices
    for col in ["nutriscore_score", "nova_group", "additives_n"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Timestamps
    for col in ["created_t", "last_modified_t"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Complétude
    if "completeness" in df.columns:
        df["completeness"] = pd.to_numeric(df["completeness"], errors="coerce").astype("float64")

    lignes_touchees = 0  # Juste typage

    return df, CompteRendu(
        regle="typer_colonnes",
        lignes_avant=len(df),
        lignes_apres=len(df),
        lignes_touchees=lignes_touchees,
        details={"colonnes_typées": len(cols_nutriments)}
    )


# ============================================================================
# RÈGLE 2 : NORMALISER LES UNITÉS
# ============================================================================

def normaliser_unites(df: pd.DataFrame) -> Tuple[pd.DataFrame, CompteRendu]:
    """
    Normalisation des unités :
    - kJ → kcal (si absent ou ratio kJ/kcal hors [3.9, 4.5])
    - sel ↔ sodium (si incohérent)
    """
    df = df.copy()
    details = {
        "kcal_derivees_kj": 0,
        "kcal_recalculees": 0,
        "sel_derive_sodium": 0,
        "sodium_derive_sel": 0,
        "sodium_recalcule": 0,
    }

    # Calcul kcal depuis kJ
    if "energy_100g" in df.columns and "energy-kcal_100g" in df.columns:
        mask_kj_present = df["energy_100g"].notna() & (df["energy_100g"] > 0)
        mask_kcal_absent = df["energy-kcal_100g"].isna()

        # Cas 1 : kJ présent, kcal absent → dériver kcal
        derive = mask_kj_present & mask_kcal_absent
        df.loc[derive, "energy-kcal_100g"] = (df.loc[derive, "energy_100g"] / KJ_PAR_KCAL).round(2)
        details["kcal_derivees_kj"] = derive.sum()

        # Cas 2 : les deux présents, ratio hors [3.9, 4.5] → recalculer kcal
        mask_both = df["energy_100g"].notna() & df["energy-kcal_100g"].notna()
        mask_both &= (df["energy_100g"] > 0) & (df["energy-kcal_100g"] > 0)

        ratio = df.loc[mask_both, "energy_100g"] / df.loc[mask_both, "energy-kcal_100g"]
        mask_incoherent = mask_both & ((ratio < 3.9) | (ratio > 4.5))

        df.loc[mask_incoherent, "energy-kcal_100g"] = (
            df.loc[mask_incoherent, "energy_100g"] / KJ_PAR_KCAL
        ).round(2)
        details["kcal_recalculees"] = mask_incoherent.sum()

    # Relation sel / sodium
    if "salt_100g" in df.columns and "sodium_100g" in df.columns:
        # Sodium théorique = sel / 2.5
        mask_sel = df["salt_100g"].notna() & (df["salt_100g"] > 0)
        mask_sodium = df["sodium_100g"].notna() & (df["sodium_100g"] > 0)

        # Dériver sodium depuis sel si absent
        derive_sodium = mask_sel & df["sodium_100g"].isna()
        df.loc[derive_sodium, "sodium_100g"] = (df.loc[derive_sodium, "salt_100g"] / SEL_PAR_SODIUM).round(4)
        details["sodium_derive_sel"] = derive_sodium.sum()

        # Dériver sel depuis sodium si absent
        derive_sel = mask_sodium & df["salt_100g"].isna()
        df.loc[derive_sel, "salt_100g"] = (df.loc[derive_sel, "sodium_100g"] * SEL_PAR_SODIUM).round(4)
        details["sel_derive_sodium"] = derive_sel.sum()

        # Recalculer sodium s'il est incohérent
        mask_both = mask_sel & mask_sodium
        sodium_attendu = df.loc[mask_both, "salt_100g"] / SEL_PAR_SODIUM
        mask_incoherent = mask_both & (np.abs(df.loc[mask_both, "sodium_100g"] - sodium_attendu) > 0.1)

        df.loc[mask_incoherent, "sodium_100g"] = (
            df.loc[mask_incoherent, "salt_100g"] / SEL_PAR_SODIUM
        ).round(4)
        details["sodium_recalcule"] = mask_incoherent.sum()

    lignes_touchees = sum([v for k, v in details.items() if isinstance(v, (int, np.integer))])

    return df, CompteRendu(
        regle="normaliser_unites",
        lignes_avant=len(df),
        lignes_apres=len(df),
        lignes_touchees=lignes_touchees,
        details=details
    )


# ============================================================================
# RÈGLE 3 : BORNER LES NUTRIMENTS
# ============================================================================

def borner_nutriments(df: pd.DataFrame) -> Tuple[pd.DataFrame, CompteRendu]:
    """
    Bornes métier sur les nutriments :
    - Négatifs → NA
    - > 100 g/100g → NA
    - sucres > glucides + 0.5 → sucres NA
    - saturés > lipides + 0.5 → saturés NA
    """
    df = df.copy()
    lignes_touchees = set()
    details = {}

    # Règle générale : négatives ou > 100 g
    for col in ["fat_100g", "saturated-fat_100g", "carbohydrates_100g", "sugars_100g",
                "fiber_100g", "proteins_100g", "salt_100g", "sodium_100g"]:
        if col in df.columns:
            mask_neg = (df[col] < 0) & df[col].notna()
            mask_over = (df[col] > 100) & df[col].notna()

            mask = mask_neg | mask_over
            lignes_touchees.update(df[mask].index)

            df.loc[mask, col] = np.nan
            details[f"{col}_invalides"] = mask.sum()

    # Cohérence sucres < glucides
    if "sugars_100g" in df.columns and "carbohydrates_100g" in df.columns:
        mask = (df["sugars_100g"] > df["carbohydrates_100g"] + 0.5) & df["sugars_100g"].notna()
        lignes_touchees.update(df[mask].index)
        df.loc[mask, "sugars_100g"] = np.nan
        details["sucres_incohérents"] = mask.sum()

    # Cohérence saturés < lipides
    if "saturated-fat_100g" in df.columns and "fat_100g" in df.columns:
        mask = (df["saturated-fat_100g"] > df["fat_100g"] + 0.5) & df["saturated-fat_100g"].notna()
        lignes_touchees.update(df[mask].index)
        df.loc[mask, "saturated-fat_100g"] = np.nan
        details["saturés_incohérents"] = mask.sum()

    return df, CompteRendu(
        regle="borner_nutriments",
        lignes_avant=len(df),
        lignes_apres=len(df),
        lignes_touchees=len(lignes_touchees),
        details=details
    )


# ============================================================================
# RÈGLE 4 : CORRIGER L'ÉNERGIE
# ============================================================================

def corriger_energie(df: pd.DataFrame) -> Tuple[pd.DataFrame, CompteRendu]:
    """
    Correction de l'énergie :
    - kcal nulles avec macronutriments → recalcul
    - kcal > 900 → recalcul ou NA
    - kcal incohérente vs calcul 4/4/9 → recalcul ou NA
    Exception : Alcoholic beverages (alcool apporte énergie)
    """
    df = df.copy()
    lignes_touchees = set()
    details = {
        "nulles_recalculees": 0,
        "over900_recalculees": 0,
        "over900_invalidees": 0,
        "incohérentes_recalculees": 0,
        "incohérentes_invalidees": 0,
    }

    if "energy-kcal_100g" not in df.columns:
        return df, CompteRendu(
            regle="corriger_energie",
            lignes_avant=len(df),
            lignes_apres=len(df),
            lignes_touchees=0,
            details=details
        )

    # Fonction de recalcul 4/4/9
    def calculer_energie(row):
        prot = row.get("proteins_100g", 0) or 0
        carb = row.get("carbohydrates_100g", 0) or 0
        fat = row.get("fat_100g", 0) or 0
        return max(0, prot * 4 + carb * 4 + fat * 9)

    # kcal nulles avec nutriments
    mask_null = df["energy-kcal_100g"].isna()
    mask_with_nutrients = (df["proteins_100g"].notna() | df["carbohydrates_100g"].notna() | df["fat_100g"].notna())
    mask_recalc = mask_null & mask_with_nutrients

    for idx in df[mask_recalc].index:
        df.loc[idx, "energy-kcal_100g"] = calculer_energie(df.loc[idx])
    details["nulles_recalculees"] = mask_recalc.sum()
    lignes_touchees.update(df[mask_recalc].index)

    # kcal > 900
    mask_over900 = (df["energy-kcal_100g"] > KCAL_MAX) & df["energy-kcal_100g"].notna()

    # Essayer recalcul si nutriments disponibles
    mask_with_nut = mask_over900 & mask_with_nutrients
    for idx in df[mask_with_nut].index:
        calc = calculer_energie(df.loc[idx])
        if calc <= KCAL_MAX:
            df.loc[idx, "energy-kcal_100g"] = calc
            details["over900_recalculees"] += 1
        else:
            df.loc[idx, "energy-kcal_100g"] = np.nan
            details["over900_invalidees"] += 1

    # Sans nutriments, juste invalider
    mask_invalid = mask_over900 & ~mask_with_nut
    df.loc[mask_invalid, "energy-kcal_100g"] = np.nan
    details["over900_invalidees"] += mask_invalid.sum()
    lignes_touchees.update(df[mask_over900].index)

    # Incohérence vs calcul 4/4/9 (si calcul ≥ 50 kcal)
    mask_with_all = (df["proteins_100g"].notna() & df["carbohydrates_100g"].notna() & df["fat_100g"].notna())
    calc_energie = df[mask_with_all].apply(lambda r: calculer_energie(r), axis=1)
    mask_calc_ok = calc_energie >= 50

    tolerance = calc_energie * 0.5  # 50% de tolérance
    mask_incoh = mask_with_all & mask_calc_ok & (
        (df["energy-kcal_100g"] - calc_energie).abs() > tolerance
    ) & df["energy-kcal_100g"].notna()

    for idx in df[mask_incoh].index:
        calc = calculer_energie(df.loc[idx])
        if calc <= KCAL_MAX:
            df.loc[idx, "energy-kcal_100g"] = calc
            details["incohérentes_recalculees"] += 1
        else:
            df.loc[idx, "energy-kcal_100g"] = np.nan
            details["incohérentes_invalidees"] += 1
    lignes_touchees.update(df[mask_incoh].index)

    return df, CompteRendu(
        regle="corriger_energie",
        lignes_avant=len(df),
        lignes_apres=len(df),
        lignes_touchees=len(lignes_touchees),
        details=details
    )


# ============================================================================
# RÈGLE 5 : DÉDUPLIQUER LES CODES
# ============================================================================

def dedupliquer_codes(df: pd.DataFrame) -> Tuple[pd.DataFrame, CompteRendu]:
    """
    Déduplication sur code-barres :
    - Normaliser (espaces)
    - Exclure lignes sans code
    - Une fiche par code : la plus complète, puis la plus récente
    """
    df = df.copy()

    # Normaliser codes (supprimer espaces)
    if "code" in df.columns:
        df["code"] = df["code"].astype(str).str.strip()

    lignes_avant = len(df)

    # Exclure sans code
    mask_with_code = df["code"].notna() & (df["code"] != "") & (df["code"] != "nan")
    sans_code = (~mask_with_code).sum()
    df = df[mask_with_code].copy()

    # Dédupliquer
    if "completeness" not in df.columns:
        # Si pas de completeness, utiliser last_modified_t
        df = df.sort_values("last_modified_t", ascending=False, na_position="last").drop_duplicates(subset=["code"], keep="first")
    else:
        # Trier par complétude (desc) puis date (desc)
        df = df.sort_values(
            ["completeness", "last_modified_t"],
            ascending=[False, False],
            na_position="last"
        ).drop_duplicates(subset=["code"], keep="first")

    lignes_apres = len(df)
    lignes_touchees = lignes_avant - lignes_apres

    return df, CompteRendu(
        regle="dedupliquer_codes",
        lignes_avant=lignes_avant,
        lignes_apres=lignes_apres,
        lignes_touchees=lignes_touchees,
        details={"sans_code_exclus": sans_code, "doublons_supprimés": lignes_touchees - sans_code}
    )


# ============================================================================
# RÈGLE 6 : TRAITER LES CATÉGORIES VIDES
# ============================================================================

def traiter_categories_vides(df: pd.DataFrame) -> Tuple[pd.DataFrame, CompteRendu]:
    """
    Gestion des catégories manquantes :
    - Rayon manquant → "unknown"
    - Drapeau pour catégorie vide
    - Exclure produits sans catégorie ET rayon unknown
    """
    df = df.copy()
    lignes_touchees = set()
    details = {
        "rayon_rempli_unknown": 0,
        "drapeau_categorie_vide": 0,
        "inclassables_exclus": 0,
    }

    # Remplir rayon manquant avec "unknown"
    if "main_category" in df.columns:
        mask_rayon_vide = df["main_category"].isna() | (df["main_category"] == "")
        df.loc[mask_rayon_vide, "main_category"] = "unknown"
        details["rayon_rempli_unknown"] = mask_rayon_vide.sum()
        lignes_touchees.update(df[mask_rayon_vide].index)

    # Drapeau catégorie vide
    if "categories_tags" in df.columns:
        mask_cat_vide = df["categories_tags"].isna() | (df["categories_tags"] == "")
        df["categorie_vide"] = mask_cat_vide.astype(int)
        details["drapeau_categorie_vide"] = mask_cat_vide.sum()
        lignes_touchees.update(df[mask_cat_vide].index)

    # Exclure inclassables (pas de catégories ET rayon unknown)
    mask_inclassable = (df["categorie_vide"] == 1) & (df["main_category"] == "unknown")
    df = df[~mask_inclassable].copy()
    details["inclassables_exclus"] = mask_inclassable.sum()

    return df, CompteRendu(
        regle="traiter_categories_vides",
        lignes_avant=len(df) + details["inclassables_exclus"],
        lignes_apres=len(df),
        lignes_touchees=len(lignes_touchees),
        details=details
    )


# ============================================================================
# RÈGLE 7 : STRATÉGIE MANQUANTS (OPTIONNEL)
# ============================================================================

STRATEGIE_PAR_DEFAUT = {
    "code": "garder",
    "product_name": "garder",
    "brands": "garder",
    "main_category": "garder",
    "categories_tags": "garder",
    "energy_100g": "garder",
    "energy-kcal_100g": "garder",
    "fat_100g": "drapeau",
    "saturated-fat_100g": "drapeau",
    "carbohydrates_100g": "drapeau",
    "sugars_100g": "drapeau",
    "fiber_100g": "drapeau",
    "proteins_100g": "drapeau",
    "salt_100g": "drapeau",
    "sodium_100g": "drapeau",
    "nutriscore_grade": "garder",
    "completeness": "garder",
}

def strategie_manquants(df: pd.DataFrame, strategie: dict = None) -> Tuple[pd.DataFrame, CompteRendu]:
    """
    Stratégie de traitement des valeurs manquantes.
    Vocabulaire fermé : garder, drapeau, supprimer_colonne
    """
    df = df.copy()
    if strategie is None:
        strategie = STRATEGIE_PAR_DEFAUT

    details = {}
    lignes_touchees = set()

    for col, decision in strategie.items():
        if col not in df.columns:
            continue

        if decision == "garder":
            pass  # Rien à faire
        elif decision == "drapeau":
            drapeau_col = f"{col}_manquant"
            mask = df[col].isna()
            df[drapeau_col] = mask.astype(int)
            details[f"{col}_drapeauté"] = mask.sum()
            lignes_touchees.update(df[mask].index)
        elif decision == "supprimer_colonne":
            if col in df.columns:
                df = df.drop(columns=[col])
                details[f"{col}_supprimé"] = True
        else:
            raise ValueError(f"Décision inconnue pour {col}: {decision}")

    # Exclure lignes sans aucun nutriment clé
    mask_no_nutrients = ~df[["energy_100g", "energy-kcal_100g", "proteins_100g", "carbohydrates_100g"]].notna().any(axis=1)
    df = df[~mask_no_nutrients].copy()
    details["lignes_sans_nutriments_exclus"] = mask_no_nutrients.sum()

    return df, CompteRendu(
        regle="strategie_manquants",
        lignes_avant=len(df) + mask_no_nutrients.sum(),
        lignes_apres=len(df),
        lignes_touchees=len(lignes_touchees),
        details=details
    )


# ============================================================================
# PIPELINE COMPLET
# ============================================================================

def nettoyer(df: pd.DataFrame, strategie: dict = None) -> Tuple[pd.DataFrame, list]:
    """
    Pipeline complet de nettoyage.
    Retourne : (DataFrame nettoyé, liste des CompteRendu)
    """
    rapports = []

    df, rapport = typer_colonnes(df)
    rapports.append(rapport)

    df, rapport = normaliser_unites(df)
    rapports.append(rapport)

    df, rapport = borner_nutriments(df)
    rapports.append(rapport)

    df, rapport = corriger_energie(df)
    rapports.append(rapport)

    df, rapport = dedupliquer_codes(df)
    rapports.append(rapport)

    df, rapport = traiter_categories_vides(df)
    rapports.append(rapport)

    df, rapport = strategie_manquants(df, strategie)
    rapports.append(rapport)

    return df, rapports
