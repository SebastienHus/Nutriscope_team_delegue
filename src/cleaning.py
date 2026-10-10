"""
Nettoyage industrialisé du catalogue NutriScope — TP 9
Module de nettoyage des données Open Food Facts avec règles pures et rejouables.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Tuple
import schema


# ============================================================================
# CONSTANTES MÉTIER
# ============================================================================

KCAL_MAX = 900.0
KCAL_MIN = 0.0
KJ_BY_KCAL = 4.184
SALT_BY_SODIUM = 2.5
ENERGY_KJ_MAX = 3000.0  # kJ très aberrant

NUTRIENTS_LIMITS = {
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

@dataclass
class Report:
    """Rapport d'exécution d'une règle de nettoyage."""
    rule: str
    lines_before: int
    lines_after: int
    lines_changed: int
    details: dict = field(default_factory=dict)

    def __str__(self):
        return (
            f"{self.rule}: {self.lines_changed} lignes touchées "
            f"({self.lines_before} → {self.lines_after})"
        )


# ============================================================================
# RÈGLE 1 : TYPAGE DES COLONNES
# ============================================================================

def type_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Report]:
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
    cols_nutriments = [c for c in df.columns if c.endswith("_100g")]
    for col in cols_nutriments:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype(float)

    # Scores / indices
    for col in ["nutriscore_score", "nova_group", "additives_n"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    # Timestamps
    for col in ["created_t", "last_modified_t"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Complétude
    if "completeness" in df.columns:
        df["completeness"] = pd.to_numeric(df["completeness"], errors="coerce").astype(float)

    lines_changed = 0  # Juste typage

    return df, Report(
        rule="typer_colonnes",
        lines_before=len(df),
        lines_after=len(df),
        lines_changed=lines_changed,
        details={"colonnes_typées": len(cols_nutriments)}
    )


# ============================================================================
# RÈGLE 2 : NORMALISER LES UNITÉS
# ============================================================================

def normalize_units(df: pd.DataFrame) -> Tuple[pd.DataFrame, Report]:
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
        mask_kcal_missing = df["energy-kcal_100g"].isna()

        # Cas 1 : kJ présent, kcal absent → dériver kcal
        derive = mask_kj_present & mask_kcal_missing
        df.loc[derive, "energy-kcal_100g"] = (df.loc[derive, "energy_100g"] / KJ_BY_KCAL).round(2)
        details["kcal_derivees_kj"] = derive.sum()

        # Cas 2 : les deux présents, ratio hors [3.9, 4.5] → recalculer kcal
        mask_both = df["energy_100g"].notna() & df["energy-kcal_100g"].notna()
        mask_both &= (df["energy_100g"] > 0) & (df["energy-kcal_100g"] > 0)

        ratio = df.loc[mask_both, "energy_100g"] / df.loc[mask_both, "energy-kcal_100g"]
        mask_incoherent = mask_both & ((ratio < 3.9) | (ratio > 4.5))

        df.loc[mask_incoherent, "energy-kcal_100g"] = (
            df.loc[mask_incoherent, "energy_100g"] / KJ_BY_KCAL
        ).round(2)
        details["kcal_recalculees"] = mask_incoherent.sum()

    # Relation sel / sodium
    if "salt_100g" in df.columns and "sodium_100g" in df.columns:
        # Sodium théorique = sel / 2.5
        mask_salt = df["salt_100g"].notna() & (df["salt_100g"] > 0)
        mask_sodium = df["sodium_100g"].notna() & (df["sodium_100g"] > 0)

        # Dériver sodium depuis sel si absent
        derive_sodium = mask_salt & df["sodium_100g"].isna()
        df.loc[derive_sodium, "sodium_100g"] = (df.loc[derive_sodium, "salt_100g"] / SALT_BY_SODIUM).round(4)
        details["sodium_derive_sel"] = derive_sodium.sum()

        # Dériver sel depuis sodium si absent
        derived_salt = mask_sodium & df["salt_100g"].isna()
        df.loc[derived_salt, "salt_100g"] = (df.loc[derived_salt, "sodium_100g"] * SALT_BY_SODIUM).round(4)
        details["sel_derive_sodium"] = derived_salt.sum()

        # Recalculer sodium s'il est incohérent
        mask_both = mask_salt & mask_sodium
        expected_sodium = df.loc[mask_both, "salt_100g"] / SALT_BY_SODIUM
        mask_incoherent = mask_both & (np.abs(df.loc[mask_both, "sodium_100g"] - expected_sodium) > 0.1)

        df.loc[mask_incoherent, "sodium_100g"] = (
            df.loc[mask_incoherent, "salt_100g"] / SALT_BY_SODIUM
        ).round(4)
        details["sodium_recalcule"] = mask_incoherent.sum()

    lines_changed = sum([v for k, v in details.items() if isinstance(v, (int, np.integer))])

    return df, Report(
        rule="normaliser_unites",
        lines_before=len(df),
        lines_after=len(df),
        lines_changed=lines_changed,
        details=details
    )


# ============================================================================
# RÈGLE 3 : BORNER LES NUTRIMENTS
# ============================================================================

def limit_nutrients(df: pd.DataFrame) -> Tuple[pd.DataFrame, Report]:
    """
    Bornes métier sur les nutriments :
    - Négatifs → NA
    - > 100 g/100g → NA
    - sucres > glucides + 0.5 → sucres NA
    - saturés > lipides + 0.5 → saturés NA
    """
    df = df.copy()
    lines_changed = set()
    details = {}

    # Règle générale : négatives ou > 100 g
    # TODO: use NUTRIENTS_LIMITS
    for col in ["fat_100g", "saturated-fat_100g", "carbohydrates_100g", "sugars_100g",
                "fiber_100g", "proteins_100g", "salt_100g", "sodium_100g"]:
        if col in df.columns:
            mask_neg = (df[col] < 0) & df[col].notna()
            mask_over = (df[col] > 100) & df[col].notna()

            mask = mask_neg | mask_over
            lines_changed.update(df[mask].index)

            df.loc[mask, col] = np.nan
            details[f"{col}_invalides"] = mask.sum()

    # Cohérence sucres < glucides
    if "sugars_100g" in df.columns and "carbohydrates_100g" in df.columns:
        mask = (df["sugars_100g"] > df["carbohydrates_100g"] + 0.5) & df["sugars_100g"].notna()
        lines_changed.update(df[mask].index)
        df.loc[mask, "sugars_100g"] = np.nan
        details["sucres_incohérents"] = mask.sum()

    # Cohérence saturés < lipides
    if "saturated-fat_100g" in df.columns and "fat_100g" in df.columns:
        mask = (df["saturated-fat_100g"] > df["fat_100g"] + 0.5) & df["saturated-fat_100g"].notna()
        lines_changed.update(df[mask].index)
        df.loc[mask, "saturated-fat_100g"] = np.nan
        details["saturés_incohérents"] = mask.sum()

    return df, Report(
        rule="borner_nutriments",
        lines_before=len(df),
        lines_after=len(df),
        lines_changed=len(lines_changed),
        details=details
    )


# ============================================================================
# RÈGLE 4 : CORRIGER L'ÉNERGIE
# ============================================================================

def revise_energy(df: pd.DataFrame) -> Tuple[pd.DataFrame, Report]:
    """
    Correction de l'énergie :
    - kcal nulles avec macronutriments → recalcul
    - kcal > 900 → recalcul ou NA
    - kcal incohérente vs calcul 4/4/9 → recalcul ou NA
    Exception : Alcoholic beverages (alcool apporte énergie)
    """
    df = df.copy()
    lines_changed = set()
    details = {
        "nulles_recalculees": 0,
        "over900_recalculees": 0,
        "over900_invalidees": 0,
        "incohérentes_recalculees": 0,
        "incohérentes_invalidees": 0,
    }

    if "energy-kcal_100g" not in df.columns:
        return df, Report(
            rule="corriger_energie",
            lines_before=len(df),
            lines_after=len(df),
            lines_changed=0,
            details=details
        )

    # Fonction de recalcul 4/4/9
    def calculate_energy(row):
        prot = row.get("proteins_100g", 0) or 0
        carb = row.get("carbohydrates_100g", 0) or 0
        fat = row.get("fat_100g", 0) or 0
        return max(0, prot * 4 + carb * 4 + fat * 9)

    # kcal nulles avec nutriments
    mask_null = df["energy-kcal_100g"].isna()
    mask_with_nutrients = (df["proteins_100g"].notna() | df["carbohydrates_100g"].notna() | df["fat_100g"].notna())
    mask_recalc = mask_null & mask_with_nutrients

    for idx in df[mask_recalc].index:
        df.loc[idx, "energy-kcal_100g"] = calculate_energy(df.loc[idx])
    details["nulles_recalculees"] = mask_recalc.sum()
    lines_changed.update(df[mask_recalc].index)

    # kcal > 900
    mask_over900 = (df["energy-kcal_100g"] > KCAL_MAX) & df["energy-kcal_100g"].notna()

    # Essayer recalcul si nutriments disponibles
    mask_with_nut = mask_over900 & mask_with_nutrients
    for idx in df[mask_with_nut].index:
        calc = calculate_energy(df.loc[idx])
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
    lines_changed.update(df[mask_over900].index)

    # Incohérence vs calcul 4/4/9 (si calcul ≥ 50 kcal)
    mask_with_all = (df["proteins_100g"].notna() & df["carbohydrates_100g"].notna() & df["fat_100g"].notna())
    df["calculated_energy"] = df[mask_with_all].apply(lambda r: calculate_energy(r), axis=1)
    mask_calc_ok = df["calculated_energy"] >= 50

    tolerance = df["calculated_energy"] * 0.5  # 50% de tolérance
    mask_incoh = mask_with_all & mask_calc_ok & (
        (df["energy-kcal_100g"] - df["calculated_energy"]).abs() > tolerance
    ) & df["energy-kcal_100g"].notna()

    for idx in df[mask_incoh].index:
        calc = calculate_energy(df.loc[idx])
        if calc <= KCAL_MAX:
            df.loc[idx, "energy-kcal_100g"] = calc
            details["incohérentes_recalculees"] += 1
        else:
            df.loc[idx, "energy-kcal_100g"] = np.nan
            details["incohérentes_invalidees"] += 1
    lines_changed.update(df[mask_incoh].index)

    return df, Report(
        rule="corriger_energie",
        lines_before=len(df),
        lines_after=len(df),
        lines_changed=len(lines_changed),
        details=details
    )


# ============================================================================
# RÈGLE 5 : DÉDUPLIQUER LES CODES
# ============================================================================

def unduplicate_codes(df: pd.DataFrame) -> Tuple[pd.DataFrame, Report]:
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

    lines_before = len(df)

    # Exclure sans code
    mask_with_code = df["code"].notna() & (df["code"] != "") & (df["code"] != "nan")
    without_code = (~mask_with_code).sum()
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

    lignes_after = len(df)
    lines_changed = lines_before - lignes_after

    return df, Report(
        rule="dedupliquer_codes",
        lines_before=lines_before,
        lines_after=lignes_after,
        lines_changed=lines_changed,
        details={"sans_code_exclus": without_code, "doublons_supprimés": lines_changed - without_code}
    )


# ============================================================================
# RÈGLE 6 : TRAITER LES CATÉGORIES VIDES
# ============================================================================

def handle_empty_categories(df: pd.DataFrame) -> Tuple[pd.DataFrame, Report]:
    """
    Gestion des catégories manquantes :
    - Rayon manquant → "unknown"
    - Drapeau pour catégorie vide
    - Exclure produits sans catégorie ET rayon unknown
    """
    df = df.copy()
    lines_changed = set()
    details = {
        "rayon_rempli_unknown": 0,
        "sous_rayon_rempli_unknown": 0,
        "categorie_remplie_tag": 0,
        "drapeau_categorie_vide": 0,
        "inclassables_exclus": 0,
    }

    # Remplir rayon manquant avec "unknown"
    if "pnns_groups_1" in df.columns:
        mask_rayon_vide = df["pnns_groups_1"].isna() | (df["pnns_groups_1"] == "")
        df.loc[mask_rayon_vide, "pnns_groups_1"] = "unknown"
        details["rayon_rempli_undefined"] = mask_rayon_vide.sum()
        lines_changed.update(df[mask_rayon_vide].index)

    # Remplir sous-rayon manquant avec "unknown"
    if "pnns_groups_2" in df.columns:
        mask_rayon_vide = df["pnns_groups_2"].isna() | (df["pnns_groups_2"] == "")
        df.loc[mask_rayon_vide, "pnns_groups_2"] = "unknown"
        details["sous_rayon_rempli_unknown"] = mask_rayon_vide.sum()
        lines_changed.update(df[mask_rayon_vide].index)

    # Drapeau catégorie vide
    if "categories_tags" in df.columns:
        mask_empty_cat = df["categories_tags"].isna() | (df["categories_tags"] == "")
        df["categorie_vide"] = mask_empty_cat.astype(int)
        details["drapeau_categorie_vide"] = mask_empty_cat.sum()
        lines_changed.update(df[mask_empty_cat].index)

    # Remplir categorie manquante avec dernier tag de la categorie
    if "main_category" in df.columns:
        mask_empty_main_category = (df["main_category"].isna() | (df["main_category"] == "")) & ~df["categorie_vide"]
        df["main_category"] = df["main_category"].astype("object") # TODO: Needs Schema and typing here
        df.loc[mask_empty_main_category, "main_category"] = df.loc[mask_empty_main_category, "categories_tags"].apply(lambda x: x.split(",")[-1])
        details["categorie_remplie_tag"] = mask_empty_main_category.sum()
        lines_changed.update(df[mask_empty_main_category].index)

    # Exclure inclassables (pas de catégories ET rayon unknown)
    mask_unclassable = (
        (df["categorie_vide"] == 1)
        & (df["main_category"].isna() | (df["main_category"] == ""))
        & (df["pnns_groups_1"] == "unknown")
    )
    df = df[~mask_unclassable].copy()
    details["inclassables_exclus"] = mask_unclassable.sum()

    return df, Report(
        rule="traiter_categories_vides",
        lines_before=len(df) + details["inclassables_exclus"],
        lines_after=len(df),
        lines_changed=len(lines_changed),
        details=details
    )


# ============================================================================
# RÈGLE 7 : STRATÉGIE MANQUANTS (OPTIONNEL)
# ============================================================================

DEFAULT_STRATEGY = {
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

def missing_strategy(df: pd.DataFrame, strategy: dict = None) -> Tuple[pd.DataFrame, Report]:
    """
    Stratégie de traitement des valeurs manquantes.
    Vocabulaire fermé : garder, drapeau, supprimer_colonne
    """
    df = df.copy()
    if strategy is None:
        strategy = DEFAULT_STRATEGY

    details = {}
    lines_changed = set()

    for col, decision in strategy.items():
        if col not in df.columns:
            continue

        if decision == "garder":
            pass  # Rien à faire
        elif decision == "drapeau":
            flag_col = f"{col}_missing"
            mask = df[col].isna()
            df[flag_col] = mask.astype(int)
            details[f"{col}_flagged"] = mask.sum()
            lines_changed.update(df[mask].index)
        elif decision == "supprimer_colonne":
            if col in df.columns:
                df = df.drop(columns=[col])
                details[f"{col}_removed"] = True
        else:
            raise ValueError(f"Décision inconnue pour {col}: {decision}")

    # Exclure lignes sans aucun nutriment clé
    mask_no_nutrients = ~df[["energy_100g", "energy-kcal_100g", "proteins_100g", "carbohydrates_100g"]].notna().any(axis=1)
    df = df[~mask_no_nutrients].copy()
    details["lignes_sans_nutriments_exclus"] = mask_no_nutrients.sum()

    return df, Report(
        rule="strategie_manquants",
        lines_before=len(df) + mask_no_nutrients.sum(),
        lines_after=len(df),
        lines_changed=len(lines_changed),
        details=details
    )


# ============================================================================
# PIPELINE COMPLET
# ============================================================================

def clean(df: pd.DataFrame, strategy: dict = None) -> Tuple[pd.DataFrame, list]:
    """
    Pipeline complet de nettoyage.
    Retourne : (DataFrame nettoyé, liste des CompteRendu)
    """
    reports = []

    # TODO: utiliser les cas d'échecs pour le nettoyage.
    _, failure_cases = schema.check_schema(df)
    if failure_cases is not None:
        print(schema.sumup(failure_cases).to_dict("records"))

    df, report = type_columns(df)
    reports.append(report)

    df, report = normalize_units(df)
    reports.append(report)

    df, report = limit_nutrients(df)
    reports.append(report)

    df, report = revise_energy(df)
    reports.append(report)

    df, report = unduplicate_codes(df)
    reports.append(report)

    df, report = handle_empty_categories(df)
    reports.append(report)

    df, report = missing_strategy(df, strategy)
    reports.append(report)

    return df, reports
