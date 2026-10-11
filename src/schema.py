"""
Schéma de validation du catalogue NutriScope (pandera).

Ce module est la source unique des constantes métier : `cleaning.py` les importe
au lieu de les redéfinir. Il fournit :

- des fonctions de contrôle vectorisées (une valeur booléenne par ligne, `True` = valide ;
  une valeur manquante est considérée comme valide : les manquants relèvent de la
  stratégie de manquants, pas des bornes) ;
- des sous-schémas de correction, utilisés par les règles de nettoyage pour pointer
  les cellules ou les lignes fautives ;
- le contrat de sortie `OUTPUT_SCHEMA`, que la sortie de `cleaning.clean()` doit respecter ;
- `find_failures()`, qui transforme les cas d'échec pandera en index de lignes par check.
"""

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors


# ============================================================================
# CONSTANTES MÉTIER
# ============================================================================

# Conversions d'unités
KJ_PER_KCAL = 4.184
SALT_PER_SODIUM = 2.5

# Énergie
KCAL_MAX = 900.0                        # 100 % de lipides = 900 kcal/100 g
KJ_MAX = KCAL_MAX * KJ_PER_KCAL         # ≈ 3 765,6 kJ/100 g
KJ_KCAL_RATIO_RANGE = (3.9, 4.5)        # rapport kJ / kcal plausible avant recalcul
KJ_KCAL_TOLERANCE_KJ = 1.0              # écart toléré entre kJ et kcal × 4,184 (arrondis)
KCAL_PER_GRAM = {                       # coefficients d'Atwater 4 / 4 / 9
    "proteins_100g": 4.0,
    "carbohydrates_100g": 4.0,
    "fat_100g": 9.0,
}
ENERGY_MIN_COMPUTED_KCAL = 50.0         # en dessous, le contrôle 4 / 4 / 9 n'est pas significatif
ENERGY_RELATIVE_TOLERANCE = 0.5         # écart toléré : 50 % de l'énergie calculée

# Cohérence entre nutriments
ROUNDING_TOLERANCE_G = 0.5              # sucres ≤ glucides + 0,5 ; saturés ≤ lipides + 0,5
SALT_SODIUM_TOLERANCE_G = 0.1           # |sel − sodium × 2,5| ≤ 0,1 g

# Bornes des nutriments en g/100 g (le sodium est borné à 40 g car sel = sodium × 2,5 ≤ 100 g)
NUTRIENT_BOUNDS = {
    "fat_100g": (0.0, 100.0),
    "saturated-fat_100g": (0.0, 100.0),
    "carbohydrates_100g": (0.0, 100.0),
    "sugars_100g": (0.0, 100.0),
    "fiber_100g": (0.0, 100.0),
    "proteins_100g": (0.0, 100.0),
    "salt_100g": (0.0, 100.0),
    "sodium_100g": (0.0, 100.0 / SALT_PER_SODIUM),
    "fruits-vegetables-legumes_100g": (0.0, 100.0),
}
ENERGY_BOUNDS = {
    "energy-kcal_100g": (0.0, KCAL_MAX),
    "energy_100g": (0.0, KJ_MAX),
}

# Complétude minimale des nutriments clés, par produit
KEY_NUTRIENTS = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
    "sugars_100g", "proteins_100g", "salt_100g",
]
KEY_NUTRIENTS_MIN_COMPLETENESS = 0.5    # au moins 4 nutriments clés sur 7

# Codes-barres officiels : EAN-8, UPC-A, EAN-13 ; préfixes GS1 200-299 = codes internes magasin
VALID_CODE_LENGTHS = (8, 12, 13)
IN_STORE_PREFIX_RANGE = (200, 299)

# Valeurs autorisées
PNNS_GROUPS = (
    "Beverages",
    "Cereals and potatoes",
    "Composite foods",
    "Fat and sauces",
    "Fish Meat Eggs",
    "Fruits and vegetables",
    "Milk and dairy products",
    "Salty snacks",
    "Sugary snacks",
    "Alcoholic beverages",
    "Baby foods",
    "unknown",
)
UNKNOWN_GROUP = "unknown"
ALCOHOL_GROUP = "Alcoholic beverages"   # l'alcool apporte une énergie hors 4 / 4 / 9

NUTRISCORE_GRADES = ("a", "b", "c", "d", "e", "not-applicable")
ENVIRONMENTAL_SCORE_GRADES = ("a-plus", "a", "b", "c", "d", "e", "f", "not-applicable")


# ============================================================================
# CONTRÔLES VECTORISÉS
# ============================================================================

def _has_columns(df: pd.DataFrame, *columns: str) -> bool:
    return all(column in df.columns for column in columns)


def _all_valid(df: pd.DataFrame) -> pd.Series:
    return pd.Series(True, index=df.index)


def is_official_length(codes: pd.Series) -> pd.Series:
    """Code composé uniquement de chiffres, de longueur 8, 12 ou 13, et pas d'un seul chiffre répété."""
    text = codes.astype("string")
    digits_only = text.str.fullmatch(r"\d+")
    valid_length = text.str.len().isin(VALID_CODE_LENGTHS)
    repeated_digit = text.str.fullmatch(r"0+|1+|2+|3+|4+|5+|6+|7+|8+|9+")
    return (digits_only & valid_length & ~repeated_digit).fillna(False).astype(bool)


def is_not_in_store(codes: pd.Series) -> pd.Series:
    """Code dont le préfixe GS1 n'est pas réservé à un usage interne (200 à 299)."""
    prefix = pd.to_numeric(codes.astype("string").str[:3], errors="coerce")
    low, high = IN_STORE_PREFIX_RANGE
    return ~prefix.between(low, high).fillna(False).astype(bool)


def compute_energy_kcal(df: pd.DataFrame) -> pd.Series:
    """Énergie calculée 4 / 4 / 9 à partir des protéines, glucides et lipides (NA si l'un manque)."""
    if not _has_columns(df, *KCAL_PER_GRAM):
        return pd.Series(np.nan, index=df.index, dtype=float)
    return sum(df[column].astype(float) * factor for column, factor in KCAL_PER_GRAM.items())


def sugars_within_carbohydrates(df: pd.DataFrame) -> pd.Series:
    """Sucres ≤ glucides + 0,5 g ; vrai si l'une des deux valeurs manque."""
    if not _has_columns(df, "sugars_100g", "carbohydrates_100g"):
        return _all_valid(df)
    return ~(df["sugars_100g"] > df["carbohydrates_100g"] + ROUNDING_TOLERANCE_G).fillna(False).astype(bool)


def saturated_within_fat(df: pd.DataFrame) -> pd.Series:
    """Acides gras saturés ≤ lipides + 0,5 g ; vrai si l'une des deux valeurs manque."""
    if not _has_columns(df, "saturated-fat_100g", "fat_100g"):
        return _all_valid(df)
    return ~(df["saturated-fat_100g"] > df["fat_100g"] + ROUNDING_TOLERANCE_G).fillna(False).astype(bool)


def salt_matches_sodium(df: pd.DataFrame) -> pd.Series:
    """|sel − sodium × 2,5| ≤ 0,1 g ; vrai si l'une des deux valeurs manque."""
    if not _has_columns(df, "salt_100g", "sodium_100g"):
        return _all_valid(df)
    gap = (df["salt_100g"] - SALT_PER_SODIUM * df["sodium_100g"]).abs()
    return ~(gap > SALT_SODIUM_TOLERANCE_G).fillna(False).astype(bool)


def kj_matches_kcal(df: pd.DataFrame) -> pd.Series:
    """
    kJ cohérents avec les kcal : rapport kJ / kcal dans [3,9 ; 4,5] (les facteurs de l'étiquetage
    européen donnent 4,18 à 4,25), ou écart |kJ − kcal × 4,184| ≤ 1 kJ pour les très faibles
    énergies (0 kcal). Vrai si l'une des deux valeurs manque.
    """
    if not _has_columns(df, "energy_100g", "energy-kcal_100g"):
        return _all_valid(df)
    kj, kcal = df["energy_100g"], df["energy-kcal_100g"]
    low, high = KJ_KCAL_RATIO_RANGE
    within_ratio = (kcal > 0) & (kj / kcal).between(low, high)
    within_gap = (kj - KJ_PER_KCAL * kcal).abs() <= KJ_KCAL_TOLERANCE_KJ
    missing = kj.isna() | kcal.isna()
    return (missing | within_ratio | within_gap).astype(bool)


def kcal_matches_macronutrients(df: pd.DataFrame) -> pd.Series:
    """
    kcal à moins de 50 % de l'énergie calculée 4 / 4 / 9, lorsque celle-ci vaut au moins 50 kcal.
    Les boissons alcoolisées sont exclues : l'alcool apporte 7 kcal/g non comptées par le calcul.
    Vrai si une valeur manque.
    """
    if "energy-kcal_100g" not in df.columns:
        return _all_valid(df)
    computed = compute_energy_kcal(df)
    gap = (df["energy-kcal_100g"] - computed).abs()
    incoherent = (computed >= ENERGY_MIN_COMPUTED_KCAL) & (gap > ENERGY_RELATIVE_TOLERANCE * computed)
    if "pnns_groups_1" in df.columns:
        incoherent &= df["pnns_groups_1"] != ALCOHOL_GROUP
    return ~incoherent.fillna(False).astype(bool)


def key_nutrients_completeness(df: pd.DataFrame) -> pd.Series:
    """Part des nutriments clés renseignés, par produit, au moins égale à 50 %."""
    present = [column for column in KEY_NUTRIENTS if column in df.columns]
    if not present:
        return pd.Series(False, index=df.index)
    completeness = df[present].notna().sum(axis=1) / len(KEY_NUTRIENTS)
    return completeness >= KEY_NUTRIENTS_MIN_COMPLETENESS


# ============================================================================
# CHECKS PANDERA (le nom `name` sert de clé stable dans find_failures)
# ============================================================================

def _code_checks() -> list[pa.Check]:
    return [
        pa.Check(is_official_length, name="official_length",
                 error=f"code de {VALID_CODE_LENGTHS} chiffres"),
        pa.Check(is_not_in_store, name="not_in_store",
                 error=f"préfixe hors {IN_STORE_PREFIX_RANGE} (code interne magasin)"),
    ]


def _bound_checks(low: float, high: float) -> list[pa.Check]:
    return [
        pa.Check.ge(low, name="min_bound"),
        pa.Check.le(high, name="max_bound"),
    ]


def _allowed_values(values: tuple[str, ...]) -> list[pa.Check]:
    return [pa.Check.isin(values, name="allowed_value")]


SUGARS_CHECK = pa.Check(sugars_within_carbohydrates, name="sugars_within_carbohydrates",
                        error="sucres ≤ glucides + 0,5 g")
SATURATED_CHECK = pa.Check(saturated_within_fat, name="saturated_within_fat",
                           error="saturés ≤ lipides + 0,5 g")
SALT_SODIUM_CHECK = pa.Check(salt_matches_sodium, name="salt_matches_sodium",
                             error="sel = sodium × 2,5")
KJ_KCAL_CHECK = pa.Check(kj_matches_kcal, name="kj_matches_kcal",
                         error="kJ = kcal × 4,184")
ENERGY_CHECK = pa.Check(kcal_matches_macronutrients, name="kcal_matches_macronutrients",
                        error="kcal cohérentes avec le calcul 4 / 4 / 9")
COMPLETENESS_CHECK = pa.Check(key_nutrients_completeness, name="key_nutrients_completeness",
                              error=f"au moins {KEY_NUTRIENTS_MIN_COMPLETENESS:.0%} des nutriments clés")


# ============================================================================
# SOUS-SCHÉMAS DE CORRECTION
# Utilisés par les règles de nettoyage pour pointer les valeurs fautives. Ils ne
# contrôlent pas les types (dtype=None) et tolèrent les colonnes absentes, pour
# qu'une règle puisse s'appliquer sur un extrait.
# ============================================================================

CODE_SCHEMA = pa.DataFrameSchema(
    {"code": pa.Column(None, _code_checks(), nullable=True, required=False)},
    name="code_rules",
)

GRADES_SCHEMA = pa.DataFrameSchema(
    {
        "nutriscore_grade": pa.Column(None, _allowed_values(NUTRISCORE_GRADES),
                                      nullable=True, required=False),
        "environmental_score_grade": pa.Column(None, _allowed_values(ENVIRONMENTAL_SCORE_GRADES),
                                               nullable=True, required=False),
    },
    name="grade_rules",
)

NUTRIENT_BOUNDS_SCHEMA = pa.DataFrameSchema(
    {
        column: pa.Column(None, _bound_checks(low, high), nullable=True, required=False)
        for column, (low, high) in NUTRIENT_BOUNDS.items()
    },
    name="nutrient_bounds",
)

NUTRIENT_CONSISTENCY_SCHEMA = pa.DataFrameSchema(
    checks=[SUGARS_CHECK, SATURATED_CHECK],
    name="nutrient_consistency",
)


# ============================================================================
# CONTRAT DE SORTIE
# ============================================================================

_output_columns = {
    "code": pa.Column(str, _code_checks(), unique=True, nullable=False),
    "product_name": pa.Column(str, [pa.Check.str_length(min_value=1, name="not_blank")], nullable=True),
    "pnns_groups_1": pa.Column(str, _allowed_values(PNNS_GROUPS), nullable=False),
    "nutriscore_grade": pa.Column(str, _allowed_values(NUTRISCORE_GRADES), nullable=True),
    "environmental_score_grade": pa.Column(str, _allowed_values(ENVIRONMENTAL_SCORE_GRADES), nullable=True),
    "created_t": pa.Column(pa.DateTime, nullable=False),
    "last_modified_t": pa.Column(pa.DateTime, nullable=False),
}
for _column, (_low, _high) in {**NUTRIENT_BOUNDS, **ENERGY_BOUNDS}.items():
    _output_columns[_column] = pa.Column(float, _bound_checks(_low, _high), nullable=True)

OUTPUT_SCHEMA = pa.DataFrameSchema(
    columns=_output_columns,
    checks=[SUGARS_CHECK, SATURATED_CHECK, SALT_SODIUM_CHECK, KJ_KCAL_CHECK,
            ENERGY_CHECK, COMPLETENESS_CHECK],
    strict=False,
    coerce=False,
    name="clean_products",
)


# ============================================================================
# EXPLOITATION DES CAS D'ÉCHEC
# ============================================================================

def find_failures(df: pd.DataFrame, schema: pa.DataFrameSchema) -> dict[str, pd.Index]:
    """
    Valide `df` en mode lazy et regroupe les lignes fautives par check.

    Les clés sont `"<colonne>:<check>"` pour un check de colonne (ex. `"fat_100g:max_bound"`)
    et `"<check>"` pour un check de DataFrame (ex. `"sugars_within_carbohydrates"`).
    Les erreurs natives de pandera (type, unicité, nullité) gardent leur libellé pandera
    (ex. `"code:field_uniqueness"`). Retourne un dictionnaire vide si tout passe.
    """
    try:
        schema.validate(df, lazy=True)
        return {}
    except SchemaErrors as errors:
        cases = errors.failure_cases

    column_names = {
        (name, number): check.name
        for name, column in schema.columns.items()
        for number, check in enumerate(column.checks)
    }
    frame_names = {number: check.name for number, check in enumerate(schema.checks)}

    keys = []
    for context, column, check, number in zip(
        cases["schema_context"], cases["column"], cases["check"], cases["check_number"]
    ):
        number = None if pd.isna(number) else int(number)
        if context == "DataFrameSchema" and number is not None:
            keys.append(frame_names.get(number, str(check)))
        else:
            keys.append(f"{column}:{column_names.get((column, number), str(check))}")

    cases = cases.assign(key=keys).dropna(subset=["index"])
    return {
        key: pd.Index(group["index"].unique())
        for key, group in cases.groupby("key", sort=True)
    }


def count_anomalies(df: pd.DataFrame) -> dict[str, int]:
    """
    Nombre de lignes en infraction par contrôle du contrat, avec les mêmes clés que
    `find_failures`, mais calculé directement par les fonctions de contrôle : utilisable
    sur des données brutes volumineuses, là où pandera listerait chaque cellule fautive.
    Les colonnes absentes sont ignorées ; `df` doit être typé (`cleaning.type_columns`).
    """
    counts = {}
    if "code" in df.columns:
        codes = df["code"].dropna()
        counts["code:official_length"] = int((~is_official_length(codes)).sum())
        counts["code:not_in_store"] = int((~is_not_in_store(codes)).sum())
        counts["code:field_uniqueness"] = int(codes.duplicated().sum())
    for column, values in (("pnns_groups_1", PNNS_GROUPS), ("nutriscore_grade", NUTRISCORE_GRADES),
                           ("environmental_score_grade", ENVIRONMENTAL_SCORE_GRADES)):
        if column in df.columns:
            present = df[column].dropna()
            counts[f"{column}:allowed_value"] = int((~present.isin(values)).sum())
    for column, (low, high) in {**NUTRIENT_BOUNDS, **ENERGY_BOUNDS}.items():
        if column in df.columns:
            counts[f"{column}:min_bound"] = int((df[column] < low).sum())
            counts[f"{column}:max_bound"] = int((df[column] > high).sum())
    for function in (sugars_within_carbohydrates, saturated_within_fat, salt_matches_sodium,
                     kj_matches_kcal, kcal_matches_macronutrients, key_nutrients_completeness):
        counts[function.__name__] = int((~function(df)).sum())
    return counts


def count_failures(failures: dict[str, pd.Index]) -> dict[str, int]:
    """Nombre de lignes fautives par check, pour un rapport ou un message d'erreur."""
    return {key: len(index) for key, index in failures.items()}
