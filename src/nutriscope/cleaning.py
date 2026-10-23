"""
Nettoyage industrialisé du catalogue NutriScope — TP 9.

Chaque règle est une fonction pure `rule(df) -> (DataFrame, Report)` :

- elle ne modifie jamais `df` (copie explicite) ;
- elle documente sa règle et ses seuils dans sa docstring ;
- ses seuils sont des constantes nommées, définies dans `schema.py` (source unique) ;
- son compte rendu compte des lignes : une ligne touchée par plusieurs sous-règles compte
  une fois dans `lines_changed` et une fois par sous-règle dans `details`.

Les règles qui invalident des valeurs (codes, grades, bornes, cohérences) s'appuient sur
les sous-schémas pandera de `schema.py` : pandera pointe les lignes fautives, la règle
décide de la correction (valeur → NA ou ligne écartée). Les règles qui recalculent
(unités, énergie) utilisent les mêmes fonctions de contrôle que le schéma.

`clean()` enchaîne les règles puis vérifie que la sortie respecte `schema.OUTPUT_SCHEMA`.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from . import schema
from .schema import (
    ALCOHOL_GROUP,
    KCAL_MAX,
    KJ_KCAL_RATIO_RANGE,
    KJ_PER_KCAL,
    PNNS_GROUPS,
    SALT_PER_SODIUM,
    SALT_SODIUM_TOLERANCE_G,
    UNKNOWN_GROUP,
)


# ============================================================================
# CONSTANTES DU MODULE
# ============================================================================

NUTRIENT_SUFFIX = "_100g"
INTEGER_COLUMNS = ("nutriscore_score", "nova_group", "additives_n")
TIMESTAMP_COLUMNS = ("created_t", "last_modified_t")   # timestamps Unix en secondes
FLOAT_COLUMNS = ("completeness",)
GRADE_COLUMNS = ("nutriscore_grade", "environmental_score_grade")
PNNS_COLUMNS = ("pnns_groups_1", "pnns_groups_2")
TAG_SEPARATOR = ","
ENERGY_DECIMALS = 2

KCAL = "energy-kcal_100g"
KJ = "energy_100g"
SALT = "salt_100g"
SODIUM = "sodium_100g"

# Check de cohérence pandera → colonne invalidée lorsqu'il échoue
CONSISTENCY_TARGETS = {
    "sugars_within_carbohydrates": "sugars_100g",
    "saturated_within_fat": "saturated-fat_100g",
}

# Vocabulaire fermé de la stratégie de manquants
KEEP = "keep"  # TODO: utiliser Enum
FLAG = "flag"
DROP_COLUMN = "drop_column"
CONSTANT_PREFIX = "constant:"
MISSING_FLAG_SUFFIX = "_missing"


@dataclass
class Report:
    """Compte rendu d'exécution d'une règle de nettoyage."""
    rule: str
    lines_before: int
    lines_after: int
    lines_changed: int
    details: dict[str, int] = field(default_factory=dict)

    def __str__(self):
        return (
            f"{self.rule}: {self.lines_changed} lignes touchées "
            f"({self.lines_before} → {self.lines_after})"
        )


# ============================================================================
# OUTILS INTERNES
# ============================================================================

def _is_blank(series: pd.Series) -> pd.Series:
    """Valeur manquante ou chaîne vide (après suppression des espaces)."""
    return series.isna() | series.astype("string").str.strip().eq("").fillna(False).astype(bool)


def _changed_rows(before: pd.DataFrame, after: pd.DataFrame, columns=None) -> pd.Series:
    """Lignes de `after` dont au moins une valeur diffère de `before` (NA ↔ valeur compte)."""
    columns = before.columns if columns is None else columns
    changed = pd.Series(False, index=after.index)
    for column in columns:
        if column not in before.columns or column not in after.columns:
            continue
        old = before.loc[after.index, column]
        new = after[column]
        same = (old == new).fillna(False).astype(bool) | (old.isna() & new.isna())
        changed |= ~same
    return changed


def _counts(details: dict) -> dict[str, int]:
    """Convertit les compteurs numpy en entiers Python (rapport lisible et sérialisable)."""
    return {key: int(value) for key, value in details.items()}


def _report(rule: str, before: pd.DataFrame, after: pd.DataFrame,
            changed: pd.Series, details: dict) -> Report:
    """Compte rendu standard : lignes modifiées parmi les conservées + lignes écartées."""
    removed = len(before) - len(after)
    return Report(
        rule=rule,
        lines_before=len(before),
        lines_after=len(after),
        lines_changed=int(changed.sum()) + removed,
        details=_counts(details),
    )


def _to_text(series: pd.Series) -> pd.Series:
    """Colonne texte : les valeurs non manquantes deviennent des `str`, les manquants restent NA."""
    if series.dtype == object or isinstance(series.dtype, pd.StringDtype):
        return series
    return series.where(series.isna(), series.astype(str)).astype(object)


# ============================================================================
# RÈGLE 1 : TYPAGE DES COLONNES
# ============================================================================

def type_columns(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Typage cohérent des colonnes.

    - nutriments (`*_100g`) et `completeness` : float64 ;
    - `nutriscore_score`, `nova_group`, `additives_n` : Int64 (entier nullable) ;
    - `created_t`, `last_modified_t` : timestamps Unix (secondes) → datetime ;
    - autres colonnes (dont `code`) : texte, manquants conservés.

    Une valeur non convertible devient NA ; ces conversions sont comptées dans
    `details["coerced_to_na"]` et ce sont les seules lignes considérées comme touchées.
    """
    out = df.copy()

    for column in out.columns:
        if column.endswith(NUTRIENT_SUFFIX) or column in FLOAT_COLUMNS:
            out[column] = pd.to_numeric(out[column], errors="coerce").astype(float)
        elif column in INTEGER_COLUMNS:
            out[column] = pd.to_numeric(out[column], errors="coerce").astype("Int64")
        elif column in TIMESTAMP_COLUMNS:
            if not pd.api.types.is_datetime64_any_dtype(out[column]):
                seconds = pd.to_numeric(out[column], errors="coerce")
                out[column] = pd.to_datetime(seconds, unit="s", errors="coerce")
        else:
            out[column] = _to_text(out[column])

    coerced = (df.notna() & out.isna()).any(axis=1)
    return out, _report("type_columns", df, out, coerced, {"coerced_to_na": coerced.sum()})


# ============================================================================
# RÈGLE 2 : NORMALISATION DES TEXTES
# ============================================================================

def normalize_texts(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Normalisation des textes.

    - `product_name` : espaces de bord retirés, nom vide → NA ;
    - grades Nutri-Score et environnemental : minuscules sans espaces, puis toute valeur
      hors `schema.NUTRISCORE_GRADES` / `schema.ENVIRONMENTAL_SCORE_GRADES` → NA
      (dont `unknown`). Les valeurs fautives sont pointées par `schema.GRADES_SCHEMA`.
    """
    out = df.copy()
    details = {}

    if "product_name" in out.columns:
        blank = _is_blank(out["product_name"]) & out["product_name"].notna()
        out["product_name"] = out["product_name"].str.strip().mask(blank)
        details["product_name_blank"] = blank.sum()

    grades = [column for column in GRADE_COLUMNS if column in out.columns]
    for column in grades:
        out[column] = out[column].str.strip().str.lower()

    failures = schema.find_failures(out[grades], schema.GRADES_SCHEMA)
    for column in grades:
        index = failures.get(f"{column}:allowed_value", pd.Index([]))
        out.loc[index, column] = np.nan
        details[f"{column}_invalidated"] = len(index)

    changed = _changed_rows(df, out, ["product_name", *grades])
    return out, _report("normalize_texts", df, out, changed, details)


# ============================================================================
# RÈGLE 3 : CODES-BARRES OFFICIELS
# ============================================================================

def filter_codes(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Ne garde que les produits à code-barres officiel.

    - tous les espaces du code sont retirés (« 301 762 042 2003 » → « 3017620422003 ») ;
    - lignes sans code écartées ;
    - lignes dont le code n'a pas 8, 12 ou 13 chiffres (`schema.VALID_CODE_LENGTHS`), ou n'est
      qu'un chiffre répété, écartées ;
    - lignes à code interne magasin (préfixe GS1 200-299, `schema.IN_STORE_PREFIX_RANGE`) écartées.

    Les codes fautifs sont pointés par `schema.CODE_SCHEMA`. Un code qui échoue aux deux
    contrôles compte dans les deux détails mais n'est écarté qu'une fois.
    """
    out = df.copy()
    code = out["code"].astype("string").str.replace(r"\s+", "", regex=True)
    code = code.mask(code.eq("").fillna(False).astype(bool))
    out["code"] = code.astype(object).where(code.notna(), np.nan)

    missing = out["code"].isna()
    failures = schema.find_failures(out.loc[~missing, ["code"]], schema.CODE_SCHEMA)
    invalid_length = failures.get("code:official_length", pd.Index([]))
    in_store = failures.get("code:not_in_store", pd.Index([]))

    removed = missing | out.index.isin(invalid_length.union(in_store))
    out = out[~removed]

    details = {
        "missing_code_removed": missing.sum(),
        "invalid_length_removed": len(invalid_length),
        "in_store_removed": len(in_store),
    }
    changed = _changed_rows(df, out, ["code"])
    return out, _report("filter_codes", df, out, changed, details)


# ============================================================================
# RÈGLE 4 : DÉDUPLICATION DES CODES
# ============================================================================

def deduplicate_codes(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Une seule fiche par code-barres.

    Parmi les doublons, on garde la fiche la plus complète (`completeness`), puis la plus
    récente (`last_modified_t`) ; tri stable, l'ordre d'origine des lignes conservées est
    préservé pour que la sortie soit reproductible. S'applique après `filter_codes`, qui
    normalise les codes et écarte les lignes sans code.
    """
    out = df.copy()
    sort_columns = [column for column in ("completeness", "last_modified_t") if column in out.columns]

    ranked = out.sort_values(sort_columns, ascending=False, na_position="last", kind="stable") \
        if sort_columns else out
    kept = ranked.drop_duplicates(subset="code", keep="first").index
    duplicated_codes = out.loc[out["code"].duplicated(keep=False), "code"].nunique()
    out = out[out.index.isin(kept)]

    details = {
        "duplicates_removed": len(df) - len(out),
        "duplicated_codes": duplicated_codes,
    }
    return out, _report("deduplicate_codes", df, out, pd.Series(False, index=out.index), details)


# ============================================================================
# RÈGLE 5 : NORMALISATION DES UNITÉS
# ============================================================================

def normalize_units(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Normalisation des unités d'énergie et du couple sel / sodium.

    - kcal ← kJ / 4,184 (`schema.KJ_PER_KCAL`) si les kcal manquent ;
    - kcal ← kJ / 4,184 si le rapport kJ / kcal sort de [3,9 ; 4,5] (`schema.KJ_KCAL_RATIO_RANGE`) ;
    - sodium ← sel / 2,5 et sel ← sodium × 2,5 (`schema.SALT_PER_SODIUM`) si l'un manque ;
    - sodium ← sel / 2,5 si |sel − sodium × 2,5| > 0,1 g (`schema.SALT_SODIUM_TOLERANCE_G`) :
      le sel, affiché sur l'étiquette, fait foi.

    Les kcal recalculées sont arrondies à 2 décimales. S'applique avant le bornage :
    une valeur dérivée aberrante est ensuite bornée.
    """
    out = df.copy()
    details = {}

    if {KCAL, KJ} <= set(out.columns):
        kcal_from_kj = (out[KJ] / KJ_PER_KCAL).round(ENERGY_DECIMALS)
        derive = out[KCAL].isna() & out[KJ].notna()
        ratio = out[KJ] / out[KCAL]
        low, high = KJ_KCAL_RATIO_RANGE
        out_of_range = (out[KJ] > 0) & (out[KCAL] > 0) & ~ratio.between(low, high)
        out[KCAL] = out[KCAL].mask(derive | out_of_range, kcal_from_kj)
        details["kcal_derived"] = derive.sum()
        details["kcal_recalculated"] = out_of_range.sum()

    if {SALT, SODIUM} <= set(out.columns):
        derive_sodium = out[SODIUM].isna() & out[SALT].notna()
        derive_salt = out[SALT].isna() & out[SODIUM].notna()
        gap = (out[SALT] - SALT_PER_SODIUM * out[SODIUM]).abs()
        recalculate_sodium = gap > SALT_SODIUM_TOLERANCE_G
        out[SODIUM] = out[SODIUM].mask(derive_sodium | recalculate_sodium, out[SALT] / SALT_PER_SODIUM)
        out[SALT] = out[SALT].mask(derive_salt, out[SODIUM] * SALT_PER_SODIUM)
        details["sodium_derived"] = derive_sodium.sum()
        details["salt_derived"] = derive_salt.sum()
        details["sodium_recalculated"] = recalculate_sodium.sum()

    changed = _changed_rows(df, out, [KCAL, KJ, SALT, SODIUM])
    return out, _report("normalize_units", df, out, changed, details)


# ============================================================================
# RÈGLE 6 : BORNAGE DES NUTRIMENTS
# ============================================================================

def bound_nutrients(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Bornes métier sur les nutriments en g/100 g.

    1. Toute valeur hors `schema.NUTRIENT_BOUNDS` (0–100 g, sodium 0–40 g) devient NA :
       une valeur impossible ne se tronque pas (74 000 g de sucres ne sont pas 100 g).
    2. Sur les valeurs restantes : sucres > glucides + 0,5 g → sucres NA ;
       saturés > lipides + 0,5 g → saturés NA (`schema.ROUNDING_TOLERANCE_G`).

    Les cellules fautives sont pointées par `schema.NUTRIENT_BOUNDS_SCHEMA` puis par
    `schema.NUTRIENT_CONSISTENCY_SCHEMA`. L'énergie est traitée par `fix_energy`.
    """
    out = df.copy()
    details = {}

    bounded = [column for column in schema.NUTRIENT_BOUNDS if column in out.columns]
    failures = schema.find_failures(out[bounded], schema.NUTRIENT_BOUNDS_SCHEMA)
    for column in bounded:
        below = failures.get(f"{column}:min_bound", pd.Index([]))
        above = failures.get(f"{column}:max_bound", pd.Index([]))
        out.loc[below.union(above), column] = np.nan
        details[f"{column}_below_min"] = len(below)
        details[f"{column}_above_max"] = len(above)

    consistency_columns = [column for column in
                           ("sugars_100g", "carbohydrates_100g", "saturated-fat_100g", "fat_100g")
                           if column in out.columns]
    failures = schema.find_failures(out[consistency_columns], schema.NUTRIENT_CONSISTENCY_SCHEMA)
    for check, column in CONSISTENCY_TARGETS.items():
        index = failures.get(check, pd.Index([]))
        out.loc[index, column] = np.nan
        details[f"{check}_invalidated"] = len(index)

    changed = _changed_rows(df, out, bounded)
    return out, _report("bound_nutrients", df, out, changed, details)


# ============================================================================
# RÈGLE 7 : CORRECTION DE L'ÉNERGIE
# ============================================================================

def fix_energy(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Correction de l'énergie à partir du calcul 4 / 4 / 9 (`schema.compute_energy_kcal`).

    Le calcul n'est utilisable que s'il est disponible (protéines, glucides et lipides
    renseignés) et plausible (≤ 900 kcal, `schema.KCAL_MAX`).

    - kcal négatives → NA ;
    - kcal manquantes ou nulles alors que le calcul est positif → calcul ;
    - kcal > 900 → calcul s'il est utilisable, sinon NA ;
    - kcal à plus de 50 % du calcul, lorsque celui-ci vaut au moins 50 kcal
      (`schema.kcal_matches_macronutrients`) → calcul s'il est utilisable, sinon NA ;
    - kJ incohérents avec les kcal (`schema.kj_matches_kcal`) ou hors bornes (0–3 766 kJ)
      réalignés sur kcal × 4,184, et NA lorsque les kcal sont NA.

    Exception : le rayon `Alcoholic beverages` n'est jamais recalculé ni complété par le
    calcul, l'alcool apportant une énergie que les macronutriments n'expliquent pas.
    S'applique après le bornage : le calcul s'appuie sur des macronutriments plausibles.
    """
    out = df.copy()
    details = {}
    if KCAL not in out.columns:
        return out, _report("fix_energy", df, out, pd.Series(False, index=out.index), details)

    computed = schema.compute_energy_kcal(out).round(ENERGY_DECIMALS)
    usable = computed.notna() & computed.between(0, KCAL_MAX)
    alcohol = out["pnns_groups_1"].eq(ALCOHOL_GROUP).fillna(False).astype(bool) \
        if "pnns_groups_1" in out.columns else pd.Series(False, index=out.index)
    kcal = out[KCAL]

    negative = kcal < 0
    kcal = kcal.mask(negative)

    missing_or_zero = (kcal.isna() | kcal.eq(0)) & ~negative & usable & (computed > 0) & ~alcohol
    kcal = kcal.mask(missing_or_zero, computed)

    over_max = kcal > KCAL_MAX
    kcal = kcal.mask(over_max & usable, computed).mask(over_max & ~usable)

    check_frame = out.assign(**{KCAL: kcal})
    incoherent = ~schema.kcal_matches_macronutrients(check_frame)
    kcal = kcal.mask(incoherent & usable, computed).mask(incoherent & ~usable)
    out[KCAL] = kcal

    details.update({
        "negative_invalidated": negative.sum(),
        "missing_or_zero_recalculated": missing_or_zero.sum(),
        "over_max_recalculated": (over_max & usable).sum(),
        "over_max_invalidated": (over_max & ~usable).sum(),
        "incoherent_recalculated": (incoherent & usable).sum(),
        "incoherent_invalidated": (incoherent & ~usable).sum(),
    })

    if KJ in out.columns:
        low, high = schema.ENERGY_BOUNDS[KJ]
        orphan_kj = out[KCAL].isna() & out[KJ].notna()
        out_of_bounds = ~out[KJ].between(low, high) & out[KJ].notna()
        misaligned = (~schema.kj_matches_kcal(out) | out_of_bounds) & ~orphan_kj
        aligned_kj = (out[KCAL] * KJ_PER_KCAL).round(ENERGY_DECIMALS)
        out[KJ] = out[KJ].mask(misaligned, aligned_kj).mask(orphan_kj)
        details["kj_realigned"] = misaligned.sum()
        details["kj_invalidated"] = orphan_kj.sum()

    changed = _changed_rows(df, out, [KCAL, KJ])
    return out, _report("fix_energy", df, out, changed, details)


# ============================================================================
# RÈGLE 8 : CATÉGORIES VIDES
# ============================================================================

# TOASK: Est-ce vraiment nécessaire ?
def _canonical_group(value: str) -> str:
    return value.strip().lower().replace("-", " ")


_PNNS_LOOKUP = {_canonical_group(group): group for group in PNNS_GROUPS}


def handle_empty_categories(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Traitement des catégories vides.

    - rayons PNNS (`pnns_groups_1`, `pnns_groups_2`) manquants → `unknown` ;
    - `pnns_groups_1` ramené à sa graphie officielle (« sugary-snacks » → « Sugary snacks »),
      toute valeur hors `schema.PNNS_GROUPS` → `unknown` ;
    - drapeau booléen `empty_category` lorsque `categories_tags` est vide ;
    - `main_category` manquante → dernier tag de `categories_tags` (le plus précis) ;
    - produits sans catégorie, sans catégorie principale **et** de rayon `unknown` : hors
      périmètre, écartés (ils ne peuvent être comparés à aucun autre produit).
    """
    out = df.copy()
    details = {}

    for column in PNNS_COLUMNS:
        if column in out.columns:
            blank = _is_blank(out[column])
            out[column] = out[column].mask(blank, UNKNOWN_GROUP)
            details[f"{column}_filled_unknown"] = blank.sum()

    if "pnns_groups_1" in out.columns:
        lookup = {value: _PNNS_LOOKUP.get(_canonical_group(value), UNKNOWN_GROUP)
                  for value in out["pnns_groups_1"].unique()}
        canonical = out["pnns_groups_1"].map(lookup)
        unrecognized = canonical.eq(UNKNOWN_GROUP) & out["pnns_groups_1"].ne(UNKNOWN_GROUP)
        details["pnns_groups_1_unrecognized"] = unrecognized.sum()
        out["pnns_groups_1"] = canonical

    empty_category = _is_blank(out["categories_tags"]) if "categories_tags" in out.columns \
        else pd.Series(True, index=out.index)
    out["empty_category"] = empty_category
    details["empty_category_flagged"] = empty_category.sum()

    if "main_category" in out.columns and "categories_tags" in out.columns:
        missing_main = _is_blank(out["main_category"]) & ~empty_category
        last_tag = out["categories_tags"].astype("string").str.split(TAG_SEPARATOR).str[-1].str.strip()
        out["main_category"] = out["main_category"].mask(missing_main, last_tag.astype(object))
        details["main_category_from_tags"] = missing_main.sum()

    no_main = _is_blank(out["main_category"]) if "main_category" in out.columns \
        else pd.Series(True, index=out.index)
    unclassifiable = empty_category & no_main & out["pnns_groups_1"].eq(UNKNOWN_GROUP) \
        if "pnns_groups_1" in out.columns else pd.Series(False, index=out.index)
    out = out[~unclassifiable]
    details["unclassifiable_removed"] = unclassifiable.sum()

    changed = _changed_rows(df, out, [*PNNS_COLUMNS, "main_category"])
    return out, _report("handle_empty_categories", df, out, changed, details)


# ============================================================================
# RÈGLE 9 : STRATÉGIE DE VALEURS MANQUANTES
# ============================================================================

DEFAULT_STRATEGY = {
    "code": KEEP,
    "product_name": KEEP,
    "brands": KEEP,
    "brands_tags": KEEP,
    "main_category": KEEP,
    "categories_tags": KEEP,
    "energy_100g": KEEP,
    "energy-kcal_100g": KEEP,
    "fat_100g": FLAG,
    "saturated-fat_100g": FLAG,
    "carbohydrates_100g": FLAG,
    "sugars_100g": FLAG,
    "fiber_100g": FLAG,
    "proteins_100g": FLAG,
    "salt_100g": FLAG,
    "sodium_100g": FLAG,
    "fruits-vegetables-legumes_100g": FLAG,
    "nutriscore_grade": KEEP,
    "completeness": KEEP,
}


def _check_strategy(strategy: dict[str, str]) -> None:
    for column, decision in strategy.items():
        if decision in (KEEP, FLAG, DROP_COLUMN) or decision.startswith(CONSTANT_PREFIX):
            continue
        raise ValueError(f"Décision inconnue pour {column} : {decision!r}")


def apply_missing_strategy(df: pd.DataFrame, strategy: dict[str, str] | None = None
                           ) -> tuple[pd.DataFrame, Report]:
    """
    Stratégie de valeurs manquantes, par colonne et par usage.

    Vocabulaire fermé (toute autre décision lève `ValueError`) :
    - `keep` : manquants conservés tels quels ;
    - `flag` : manquants conservés + colonne booléenne `<colonne>_missing` (manquants MNAR) ;
    - `constant:<valeur>` : manquants remplacés par la valeur (convertie en nombre pour
      une colonne numérique) ;
    - `drop_column` : colonne supprimée.

    Les produits dont moins de 50 % des nutriments clés sont renseignés
    (`schema.key_nutrients_completeness`) sont écartés. Aucune imputation statistique
    (médiane, KNN) n'est faite ici : elle appartient au pipeline ML, après le split.
    Les drapeaux ne comptent pas comme lignes touchées (seules les valeurs remplacées et
    les lignes écartées comptent), ce qui garde la règle idempotente.
    """
    strategy = DEFAULT_STRATEGY if strategy is None else strategy
    _check_strategy(strategy)

    out = df.copy()
    insufficient = ~schema.key_nutrients_completeness(out)
    out = out[~insufficient]
    details = {"insufficient_key_nutrients_removed": insufficient.sum(), "columns_dropped": 0}

    for column, decision in strategy.items():
        if column not in out.columns:
            continue
        missing = out[column].isna()
        if decision == FLAG:
            out[f"{column}{MISSING_FLAG_SUFFIX}"] = missing
            details[f"{column}_flagged"] = missing.sum()
        elif decision.startswith(CONSTANT_PREFIX):
            value = decision.removeprefix(CONSTANT_PREFIX)
            if pd.api.types.is_numeric_dtype(out[column]):
                value = float(value)
            out[column] = out[column].mask(missing, value)
            details[f"{column}_filled"] = missing.sum()
        elif decision == DROP_COLUMN:
            out = out.drop(columns=column)
            details["columns_dropped"] += 1

    changed = _changed_rows(df, out)
    return out, _report("apply_missing_strategy", df, out, changed, details)


# ============================================================================
# CONTRAT DE SORTIE
# ============================================================================

def validate_output(df: pd.DataFrame) -> tuple[pd.DataFrame, Report]:
    """
    Vérifie que `df` respecte `schema.OUTPUT_SCHEMA` (types, bornes, valeurs autorisées,
    unicité des codes, cohérences entre nutriments, complétude).

    Ne modifie rien : lève `ValueError` avec le nombre de lignes fautives par check si le
    contrat n'est pas respecté. Une sortie qui échoue signale une règle manquante ou fausse.
    """
    failures = schema.find_failures(df, schema.OUTPUT_SCHEMA)
    if failures:
        raise ValueError(
            "La sortie du nettoyage ne respecte pas le schéma : "
            f"{schema.count_failures(failures)}"
        )
    checks = sum(len(column.checks) for column in schema.OUTPUT_SCHEMA.columns.values())
    checks += len(schema.OUTPUT_SCHEMA.checks)
    return df, _report("validate_output", df, df, pd.Series(False, index=df.index),
                       {"checks_passed": checks})


# ============================================================================
# PIPELINE COMPLET
# ============================================================================

CLEANING_RULES = (
    type_columns,
    normalize_texts,
    filter_codes,
    deduplicate_codes,
    normalize_units,
    bound_nutrients,
    fix_energy,
    handle_empty_categories,
)


def clean(df: pd.DataFrame, strategy: dict[str, str] | None = None
          ) -> tuple[pd.DataFrame, list[Report]]:
    """
    Pipeline complet de nettoyage, dans l'ordre conseillé par le TP :
    types, textes, codes, doublons, unités, bornes, énergie, catégories, manquants,
    puis validation de la sortie contre `schema.OUTPUT_SCHEMA`.

    Retourne le DataFrame nettoyé et la liste des comptes rendus (un par règle).
    """
    reports = []
    for rule in CLEANING_RULES:
        df, report = rule(df)
        reports.append(report)

    df, report = apply_missing_strategy(df, strategy)
    reports.append(report)

    df, report = validate_output(df)
    reports.append(report)

    return df, reports
