import pandas as pd
import numpy as np
import pandera.pandas as pa
from pandera.errors import SchemaErrors

GROUPS = [
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
    "unknown"
]

GRADES = ["a", "b", "c", "d", "e", "not-applicable"]

COMPLETUDE_THRESHOLD = 0.5  # 50% de complétude minimal pour nutriments clés
KEY_NUTRIENTS = [
    "energy-kcal_100g", "fat_100g", "saturated-fat_100g", "carbohydrates_100g",
    "sugars_100g", "proteins_100g", "salt_100g",
]

VALID_CODE_LENGTHS = (8, 12, 13)

NUTRIENTS_LIMITS = {
    "fat_100g": (0, 100),
    "saturated-fat_100g": (0, 100),
    "carbohydrates_100g": (0, 100),
    "sugars_100g": (0, 100),
    "fiber_100g": (0, 100),
    "proteins_100g": (0, 100),
    "salt_100g": (0, 100),
    "sodium_100g": (0, 40), # sel ≤ 100
    "fruits-vegetables-legumes_100g": (0, 100),
    "energy-kcal_100g": (0, 900),
    "energy_100g": (0, 3500),  # kJ (900 kcal ≈ 3765 kJ)
}

def get_code_length(code):
    if not isinstance(code, str) or not code.isdecimal():
        return 0
    code_length = len(code)
    # Vérifie si le code a seulement un même numéro dans la séquence
    if code[0] * code_length != code:
        return code_length
    return -1

def check_code_length(code):
    return get_code_length(code) in VALID_CODE_LENGTHS

def is_in_store_coding(code):
    if code is np.nan:
        return False
    
    if (
        not isinstance(code, str)
        or not code.isdecimal()
        or len(code) < 3
    ):
        return False
    
    return 200 <= int(code[:3]) <= 299

def sugars_less_than_carbohydrates(df: pd.DataFrame) -> pd.Series:
    """Vérifie multi-colonnes : sucres ≤ glucides (+ 0,5 g de tolérance d'arrondi) ; vrai si l'un manque."""
    return ~(df["sugars_100g"] > df["carbohydrates_100g"] + 0.5)

def salt_equals_sodium(df: pd.DataFrame) -> pd.Series:
    """Vérifie multi-colonnes : |sel − sodium × 2,5| ≤ 0,1 ; vrai si l'un manque."""
    return ~((df["salt_100g"] - 2.5 * df["sodium_100g"]).abs() > 0.1)

def minimal_nutrients_completude(df: pd.DataFrame) -> pd.Series:
    """Vérifie multi-colonnes : complétude minimal pour les nutriments clés."""
    return ~(df[KEY_NUTRIENTS].isna().mean() > COMPLETUDE_THRESHOLD)

def energy_equivalence(df: pd.DataFrame) -> pd.Series:
    """Vérifie multi-colonnes : |energy − energy_kcal × 4,184| ≤ 0,1 ; vrai si l'un manque."""
    return ~((df["energy_100g"] - 4.184 * df["energy-kcal_100g"]).abs() > 0.1)

def calculate_energy(df: pd.DataFrame) -> pd.Series:
    prot = df["proteins_100g"]
    carb = df["carbohydrates_100g"]
    fat = df["fat_100g"]
    try:
        return prot * 4.0 + carb * 4.0 + fat * 9.0
    except TypeError:
        pass
    return pd.Series(np.nan, index=df.index)

def energy_calculation(df: pd.DataFrame) -> pd.Series:
    """Vérifie multi-colonnes : energy_kcal = prot * 4 + carb * 4 + fat * 9 (+ 0,5 g de tolérance d'arrondi) ; vrai si l'un manque."""
    return ~(df["energy-kcal_100g"] - calculate_energy(df) > calculate_energy(df) + 0.5)

columns = {
    "code": pa.Column(str, [
        pa.Check(check_code_length, error=f"Longueur de code officiel {VALID_CODE_LENGTHS}"),
        pa.Check(is_in_store_coding, error="Code non interne")
        ], unique=True, nullable=False, coerce=True),
    "product_name": pa.Column(str, [pa.Check.str_length(min_value=1)], nullable=True, coerce=True),
    "pnns_groups_1": pa.Column(str, [pa.Check.isin(GROUPS, error="rayon PNNS connu")], nullable=False, coerce=True),
    "nutriscore_grade": pa.Column(str, [pa.Check.isin(GRADES, error="grade a-e ou not-applicable")],
                                    nullable=True, coerce=True),
    "created_t": pa.Column(pa.DateTime, nullable=False),
    "last_modified_t": pa.Column(pa.DateTime, nullable=False)
}

for column, (limit_min, limit_max) in NUTRIENTS_LIMITS.items():
    unit = "g"
    match column:
        case "energy-kcal_100g":
            unit = "kcal"
        case "energy_100g":
            unit = "kJ"
    
    columns[column] = pa.Column(
        float,
        [pa.Check.in_range(limit_min, limit_max, error=f"{limit_min}-{limit_max} {unit}/100 g")],
        nullable=True
    )

SCHEMA_PRODUITS = pa.DataFrameSchema(
    columns=columns,
    checks=[
        pa.Check(sugars_less_than_carbohydrates, error="sucres ≤ glucides"),
        pa.Check(salt_equals_sodium, error="sel = sodium × 2,5"),
        pa.Check(minimal_nutrients_completude, error="complétude des nutriments clés ≥ 0.5"),
        pa.Check(energy_equivalence, error="kJ = kcal × 4,184"),
        pa.Check(energy_calculation, error="energy_kcal = prot*4 + carb*4 + fat*9")
    ],
    strict=False,
    name="produits_nettoyes",
)


def check_schema(df: pd.DataFrame) -> tuple[bool, pd.DataFrame | None]:
    """Valide en `lazy` mode : (True, None) si tout passe, sinon (False, tableau des cas d'échec)."""
    try:
        SCHEMA_PRODUITS.validate(df, lazy=True)
        return True, None
    except SchemaErrors as erreurs:
        return False, erreurs.failure_cases


def sumup(failure_case: pd.DataFrame) -> pd.DataFrame:
    """Nombre de cas d'échec par check : lignes pour un check de colonne, lignes distinctes pour un check de DataFrame
    (Pandera rapporte alors chaque colonne de la ligne fautive, ce qui multiplierait les cas)."""
    columns = failure_case[failure_case["schema_context"] == "Column"].groupby(["column", "check"]).size()
    dataframe = failure_case[failure_case["schema_context"] == "DataFrameSchema"].groupby("check")["index"].nunique()
    dataframe.index = pd.MultiIndex.from_tuples([("[règle métier]", c) for c in dataframe.index], names=["column", "check"])
    return pd.concat([columns, dataframe]).rename("echec").reset_index()