import pandas as pd
import numpy as np

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
        nrows=10000
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

def clean_products_data(df):
    _df = df.copy()

    nutriment_columns = get_nutriment_columns(_df)
    for col in nutriment_columns:
        _df[col] = pd.to_numeric(_df[col], errors="coerce")

    # Filtrage des codes commençant par 200. Ce sont des produits non codés, on ne les garde pas
    _df = _df[~_df["code"].str.startswith("200", na=False)]
    
    # Filtrage des codes non officiels. Les officiels sont composés de 8, 12 et 13 digits
    _df["code"] = _df["code"].apply(lambda x: x if check_code(x) in VALID_CODE_LENGTH else np.nan)

    # Filtrage des notes nutriscores invalides
    _df["nutriscore_grade"] = _df["nutriscore_grade"].apply(check_nutriscore)

    # Filtrage des notes d'environnement invalides
    _df["environmental_score_grade"] = _df["environmental_score_grade"].apply(check_nutriscore)

    for col in nutriment_columns[:1]:
        _df[col] = _df[col].apply(check_energy)
    for col in nutriment_columns[1:]:
        _df[col] = _df[col].apply(check_nutriment)

    _df.dropna(subset=nutriment_columns, inplace=True)

    return _df