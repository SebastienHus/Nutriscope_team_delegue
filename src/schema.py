import pandas as pd
import pandera as pa
from pandera.errors import SchemaErrors

RAYONS = [
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


def sugars_less_than_carbohydrates(df: pd.DataFrame) -> pd.Series:
    """Check multi-colonnes : sucres ≤ glucides (+ 0,5 g de tolérance d'arrondi) ; vrai si l'un manque."""
    return ~(df["sugars_100g"] > df["carbohydrates_100g"] + 0.5)


def salt_equals_sodium(df: pd.DataFrame) -> pd.Series:
    """Check multi-colonnes : |sel − sodium × 2,5| ≤ 0,1 ; vrai si l'un manque."""
    return ~((df["salt_100g"] - 2.5 * df["sodium_100g"]).abs() > 0.1)


SCHEMA_PRODUITS = pa.DataFrameSchema(
    columns={
        "code": pa.Column(str, [pa.Check.str_matches(r"^\d{4,}$", error="code numérique (4 chiffres au moins)")],
                          unique=True, nullable=False, coerce=True),
        "product_name": pa.Column(str, [pa.Check.str_length(min_value=1)], nullable=True, coerce=True),
        "pnns_groups_1": pa.Column(str, [pa.Check.isin(RAYONS, error="rayon PNNS connu")], nullable=False, coerce=True),
        "nutriscore_grade": pa.Column(str, [pa.Check.isin(["a", "b", "c", "d", "e", "not-applicable"], error="grade a-e ou not-applicable")],
                                      nullable=True, coerce=True),
        "energy-kcal_100g": pa.Column(float, [pa.Check.in_range(0, 900, error="0-900 kcal/100 g")], nullable=True),
        "fat_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "carbohydrates_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "sugars_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "salt_100g": pa.Column(float, [pa.Check.in_range(0, 100, error="0-100 g/100 g")], nullable=True),
        "sodium_100g": pa.Column(float, [pa.Check.in_range(0, 40, error="0-40 g/100 g (sel ≤ 100)")], nullable=True),
    },
    checks=[
        pa.Check(sugars_less_than_carbohydrates, error="sucres ≤ glucides"),
        pa.Check(salt_equals_sodium, error="sel = sodium × 2,5"),
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
    dataframe.index = pd.MultiIndex.from_tuples([("(ligne)", c) for c in dataframe.index], names=["column", "check"])
    return pd.concat([columns, dataframe]).rename("echec").reset_index()