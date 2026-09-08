import pandas as pd
import numpy as np
from functools import partial

VALID_CODE_LENGTH = (8, 12, 13)
NUTRISCORE_GRADES = "abcde"


def read_products_data(data_path, columns=None):
    dtypes = {"code": "str"}
    chunks = pd.read_csv(
        data_path,
        sep="\t",
        usecols=columns,
        iterator=True,
        chunksize=1000,
        on_bad_lines="warn",
        dtype=dtypes,
        # nrows=10000
    )

    return pd.concat(chunks, ignore_index=True)

def get_nutriment_columns(data):
    return [column for column in data.columns if column.endswith("_100g")]

def check_nutriscore(value):
    if isinstance(value, str) and value in NUTRISCORE_GRADES:
        return value
    return np.nan

def check_nutriment(value):
    # Ne peut excéder 100 ou être négatif
    if value > 100 or value < 0:
        return np.nan
    return value

def check_energy(value):
    # Ne peut être nul ou négatif
    if value <= 0:
        return np.nan
    return value

def check_code(code):
    if not isinstance(code, str) or not code.isdecimal():
        return 0
    code_length = len(code)
    # Vérifie si le code a seulement un même numéro dans la séquence
    if code[0] * code_length != code:
        return code_length
    return -1

def check_brand(value):
    if len(value) > 255: # Valeur absurde
        return np.nan
    if value == "xx:none":
        return np.nan

    return value

def check_category(value):
    if len(value) > 255: # Valeur absurde
        return np.nan
    if value == "en:undefined":
        return np.nan

    return value

def to_list(value, func = None):
    func = func or (lambda x: x)
    if not isinstance(value, str):
        return []
    return [func(v.strip()) for v in value.split(",")]

def clean_products_data(df: pd.DataFrame):
    _df = df.copy()

    nutriment_columns = get_nutriment_columns(_df)
    for col in nutriment_columns:
        _df[col] = pd.to_numeric(_df[col], errors="coerce")

    # Nettoyage des tags
    _df["food_groups_tags"] = _df["food_groups_tags"].apply(to_list)
    _df["categories_tags"] = _df["categories_tags"].apply(partial(to_list, func=check_category))
    _df["brands_tags"] = _df["brands_tags"].apply(partial(to_list, func=check_brand))
    _df["additives_tags"] = _df["additives_tags"].apply(to_list)
    _df["labels_tags"] = _df["labels_tags"].apply(partial(to_list, func=check_category))
    _df["allergens"] = _df["allergens"].apply(to_list)
    _df["traces_tags"] = _df["traces_tags"].apply(partial(to_list, func=check_category))
    _df["countries_tags"] = _df["countries_tags"].apply(to_list)

    _df["nutriscore_score"] = pd.to_numeric(_df["nutriscore_score"], errors="coerce")
    _df["nova_group"] = pd.to_numeric(_df["nova_group"], errors="coerce")

    # Filtrage des codes commençant par 200. Ce sont des produits non codés, on ne les garde pas
    _df = _df[~_df["code"].str.startswith("200", na=False)]
    
    # Filtrage des codes non officiels. Les officiels sont composés de 8, 12 et 13 digits
    _df["code"] = _df["code"].apply(lambda x: x if check_code(x) in VALID_CODE_LENGTH else np.nan)

    # Filtrage des produits sans nom ou sans code
    _df.dropna(subset=["code", "product_name"], inplace=True)

    # Filtrage des notes nutriscores invalides
    _df["nutriscore_grade"] = _df["nutriscore_grade"].apply(check_nutriscore)

    # Filtrage des notes d'environnement invalides, pareil que le nutriscore
    _df["environmental_score_grade"] = _df["environmental_score_grade"].apply(check_nutriscore)

    function_to_apply = {"energy_100g": check_energy}
    for col in nutriment_columns:
        _df[col] = _df[col].apply(function_to_apply.get(col, check_nutriment))

    _df.dropna(subset=nutriment_columns, inplace=True)

    return _df