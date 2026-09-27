from dataclasses import field, dataclass
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

KCAL_MAX = 900.0
"""Valeur de kcal max pour 100g"""
SALT_BY_SODIUM = 2.5
"""Facteur d'équivalence sel ↔ sodium : sel = 2.5 * sodium"""
KJ_BY_KCAL = 4.184
"""Facteur d'équivalence kJ ↔ kcal : kJ = 4.184 * kcal"""

GRADES = ["a", "b", "c", "d", "e", "not-applicable"]
GROUPS = [
    "Beverages", "Cereals and potatoes", "Composite foods", "Fat and sauces", "Fish Meat Eggs",
    "Fruits and vegetables", "Milk and dairy products", "Salty snacks", "Sugary snacks",
    "Alcoholic beverages", "Baby foods", "unknown"
]

def sugars_inf_carbohydrates(df: pd.DataFrame) -> pd.Series:
    """Check multi-colonnes : sucres ≤ glucides (+ 0,5 g de tolérance d'arrondi) ; vrai si l'un manque."""
    return ~(df["sugars_100g"] > df["carbohydrates_100g"] + 0.5)


def salt_equals_sodium(df: pd.DataFrame) -> pd.Series:
    """Check multi-colonnes : |sel − sodium × 2,5| ≤ 0,1 ; vrai si l'un manque."""
    return ~((df["salt_100g"] - 2.5 * df["sodium_100g"]).abs() > 0.1)

DF_SCHEMA = pa.DataFrameSchema(
    columns={
        "code": pa.Column(str, [pa.Check.str_matches(r"^\d{4,}$", error="code numérique (4 chiffres au moins)")],
                          unique=True, nullable=False, coerce=True),
        "product_name": pa.Column(str, [pa.Check.str_length(min_value=1)], nullable=True, coerce=True),
        "pnns_groups_1": pa.Column(str, [pa.Check.isin(GROUPS, error="rayon PNNS connu")], nullable=False, coerce=True),
        "nutriscore_grade": pa.Column(str, [pa.Check.isin(GRADES, error="grade a-e ou not-applicable")],
                                      nullable=True, coerce=True),
        "energy-kcal_100g": pa.Column(float, [pa.Check.in_range(0, 900, error="0-900 kcal/100 g")], nullable=True),
        "fat_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "carbohydrates_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "sugars_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "salt_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "sodium_100g": pa.Column(float, [pa.Check.in_range(0, 40, error="0-40 g/100 g (sel ≤ 100)")], nullable=True),
    },
    checks=[
        pa.Check(sugars_inf_carbohydrates, error="sucres ≤ glucides"),
        pa.Check(salt_equals_sodium, error="sel = sodium × 2,5"),
    ],
    strict=False,
    name="produits_nettoyes",
)

@dataclass
class Report:
    rule: str
    lines_before: int
    lines_after: int
    lines_changed: int
    details: dict[str, int] = field(default_factory=dict)

def safe_data_frame(outer):
    def inner(df: pd.DataFrame, *args, **kwargs):
        return outer(df.copy(), *args, **kwargs)
    return inner


# def rule(def: pd.DataFrame) -> tuple[pd.DataFrame, Report]
def assert_frame():
    pd.testing.assert_frame_equal(entree, copie)

def convert_to_energy(carbohydrates, proteins, fat):
    return 4 * carbohydrates + 4 * proteins + 9 * fat

@safe_data_frame
def normalize_energy(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Report]]:
    kcal = df["energy-kcal_100g"]
    from_kj = kcal.isna() & df["energy_100g"].notna()
    kcal = kcal.mask(from_kj, (df["energy_100g"] / KJ_BY_KCAL).round(1))
    calc = convert_to_energy(df["carbohydrates_100g"], df["proteins_100g"], df["fat_100g"])
    from_macros = kcal.isna() & calc.notna() & (calc <= KCAL_MAX)
    kcal = kcal.mask(from_macros, calc.round(1))
    df["energy-kcal_100g"] = kcal
    details = {"from_kj": int(from_kj.sum()), "from_macros": int(from_macros.sum()), "restant": int(kcal.isna().sum())}
    report = Report(
        "normalize_energy",
        lines_before=0,
        lines_after=0,
        lines_changed=details["from_kj"] + details["from_macros"],
        details=details
    )
    return df, report

@safe_data_frame
def impute_salt_sodium(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Report]]:
    """3. Sel et sodium : relation exacte dans les deux sens."""
    salt, sodium = df["salt_100g"], df["sodium_100g"]
    salt_ok = salt.isna() & sodium.notna()
    sodium_ok = sodium.isna() & salt.notna()
    df["salt_100g"] = salt.mask(salt_ok, sodium * 2.5)
    df["sodium_100g"] = sodium.mask(sodium_ok, salt / 2.5)
    details = {"salt_from_sodium": int(salt_ok.sum()), "sodium_from_salt": int(sodium_ok.sum()), "restant": int(df["salt_100g"].isna().sum())}
    report = Report("Imputing salt, sodium", lines_before=0, lines_after=0, lines_changed=details["salt_from_sodium"] + details["sodium_from_salt"])
    return df, report

@safe_data_frame
def normalize_units(df: pd.DataFrame):
    pass

@safe_data_frame
def limit_nutriments(df: pd.DataFrame):
    pass

@safe_data_frame
def rectify_energy(df: pd.DataFrame):
    pass

@safe_data_frame
def drop_codes_duplicate(df: pd.DataFrame):
    pass

@safe_data_frame
def handle_empty_categories(df: pd.DataFrame):
    pass

@safe_data_frame
def normalize_texts(df: pd.DataFrame):
    pass