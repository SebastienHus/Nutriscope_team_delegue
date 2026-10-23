"""
Bibliothèque commune de la phase 4 : prédire le Nutri-Score (TP 14) et comparer les
méthodes d'ensemble (TP 15) à conditions égales.

Les quatre conditions d'égalité du TP 15 vivent ici, et nulle part ailleurs :

| Condition        | Objet unique                                              |
| ---------------- | --------------------------------------------------------- |
| même préparation | `preparation()`, appelée par `make_model()`               |
| mêmes plis       | `make_cv()` : `StratifiedKFold(5, shuffle=True, seed 42)` |
| mêmes métriques  | `SCORING`, utilisé par `cross_validate_models()`          |
| même `split`     | `split_frame()`, qui lit la colonne figée du TP 13        |

Règles d'usage : `fit` sur le train seulement ; la validation croisée se fait à
l'intérieur du train ; le test n'est regardé qu'une fois, à la fin (`test_scores()`).
`code`, `product_name`, `brands`, `split` et `nutriscore_score` ne sont jamais des
features : `check_no_leak()` le garantit.

Données : © Open Food Facts contributors — ODbL.
"""

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin, clone
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score, accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler

from .options import RANDOM_SEED, SHARED_DATA_PATH
from .schema import KCAL_PER_GRAM, KEY_NUTRIENTS

# ============================================================================
# CONSTANTES
# ============================================================================

DATA_ENV = "NUTRISCOPE_DATA"
ML_SAMPLE = "nutriscope_ml_sample.parquet"

TARGET = "nutriscore_grade"
GRADES = ("a", "b", "c", "d", "e")
SPLIT = "split"
TRAIN, TEST = "train", "test"

# Jamais des features : identifiants, split, et le score dont le grade est dérivé (fuite)
IDENTIFIERS = ("code", "product_name", "brands")
LEAKY = ("nutriscore_score",)
FORBIDDEN_FEATURES = (*IDENTIFIERS, SPLIT, *LEAKY)

# Les 13 colonnes brutes utilisées comme features, dans un ordre fixe
CATEGORICAL = ("pnns_groups_1", "pnns_groups_2")
OPTIONAL = ("fiber_100g", "fruits-vegetables-legumes_100g", "nova_group", "additives_n")
NUTRIENTS = tuple(KEY_NUTRIENTS)
FEATURES = (*CATEGORICAL, *NUTRIENTS, *OPTIONAL)

# Features dérivées, calculées dans le pipeline (jamais à la main sur le DataFrame)
DERIVED = ("ratio_sugars_carbs", "ratio_satfat_fat", "ratio_energy_fat", "energy_gap_kcal")

N_FOLDS = 5
MIN_CATEGORY_COUNT = 50     # un rayon vu moins de 50 fois au fit rejoint la modalité « rare »
SCORING = {
    "f1_macro": "f1_macro",
    "accuracy": "accuracy",
    "balanced_accuracy": "balanced_accuracy",
}


# ============================================================================
# DONNÉES
# ============================================================================

def data_dir() -> Path:
    """Dossier du jeu partagé : `$NUTRISCOPE_DATA` (dossier ou fichier), sinon `data-nutriscope/`."""
    env = os.environ.get(DATA_ENV)
    if env:
        path = Path(env).expanduser().resolve()
        return path.parent if path.is_file() else path
    return SHARED_DATA_PATH


def dataset_path(name: str = ML_SAMPLE) -> Path:
    """Chemin du jeu ML, rangé dans `ml/` ou à la racine du dossier partagé."""
    folder = data_dir()
    for candidate in (folder / "ml" / name, folder / name):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"{name} not found in {folder} or {folder / 'ml'}: set {DATA_ENV}")


def load_dataset(path: Path | None = None) -> pd.DataFrame:
    """Charge le jeu ML et vérifie qu'il porte la cible et la colonne `split` figée."""
    df = pd.read_parquet(path or dataset_path())
    missing = [column for column in (TARGET, SPLIT, *FEATURES) if column not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in the ML dataset: {missing}")
    return df


def check_no_leak(columns) -> None:
    """Lève `ValueError` si une colonne interdite (identifiant, split, score) est une feature."""
    leaks = [column for column in columns if column in FORBIDDEN_FEATURES]
    if leaks:
        raise ValueError(f"Forbidden feature columns: {leaks}")


def encode_grades(grades) -> np.ndarray:
    """Grades a-e → entiers 0-4 (codage fixe, le même pour tous les modèles)."""
    codes = pd.Series(np.asarray(grades, dtype=object)).map({grade: i for i, grade in enumerate(GRADES)})
    if codes.isna().any():
        raise ValueError("Unknown grade in target")
    return codes.to_numpy(dtype=int)


def decode_grades(codes) -> np.ndarray:
    """Entiers 0-4 → grades a-e."""
    return np.asarray(GRADES)[np.asarray(codes).ravel().astype(int)]


def split_frame(df: pd.DataFrame, features=FEATURES, allow_leak: bool = False
                ) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray]:
    """
    `X_train, X_test, y_train, y_test` selon la colonne `split` figée du TP 13 (jamais
    recalculée). La cible est codée 0-4. `allow_leak=True` n'est permis que pour
    reproduire volontairement une fuite (TP 14, étape 4a).
    """
    features = list(features)
    if not allow_leak:
        check_no_leak(features)
    train, test = df[SPLIT] == TRAIN, df[SPLIT] == TEST
    if not (train | test).all():
        raise ValueError(f"Unexpected values in `{SPLIT}`: {sorted(df[SPLIT].unique())}")
    return (df.loc[train, features], df.loc[test, features],
            encode_grades(df.loc[train, TARGET]), encode_grades(df.loc[test, TARGET]))


# ============================================================================
# PRÉPARATION
# ============================================================================

def add_derived_features(X: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute les ratios et l'écart d'énergie, et passe les numériques en `float64` (les
    entiers nullables `Int64` deviennent des réels avec NaN). Fonction pure : `X` intact.
    """
    out = X.copy()
    numeric = [column for column in out.columns if column not in CATEGORICAL]
    out[numeric] = out[numeric].astype("float64")

    def ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
        return (numerator / denominator.where(denominator > 0)).fillna(0.0)

    computed_kcal = sum(out[column] * factor for column, factor in KCAL_PER_GRAM.items())
    out["ratio_sugars_carbs"] = ratio(out["sugars_100g"], out["carbohydrates_100g"])
    out["ratio_satfat_fat"] = ratio(out["saturated-fat_100g"], out["fat_100g"])
    out["ratio_energy_fat"] = ratio(out["fat_100g"] * KCAL_PER_GRAM["fat_100g"], out["energy-kcal_100g"])
    out["energy_gap_kcal"] = out["energy-kcal_100g"] - computed_kcal
    return out


def _derived_names(transformer, input_features) -> list[str]:
    return [*input_features, *DERIVED]


def preparation(min_frequency: int = MIN_CATEGORY_COUNT) -> Pipeline:
    """
    Préparation commune à tous les modèles, ajustée dans le pipeline (donc sur le seul
    train de chaque pli) :

    - features dérivées (`add_derived_features`) ;
    - nutriments obligatoires et dérivées : imputation médiane, standardisation ;
    - colonnes optionnelles (fibres, fruits-légumes, NOVA, additifs) : imputation médiane
      avec indicateur de manquant, standardisation ;
    - rayons : one-hot, catégories inconnues ignorées, rayons rares regroupés.
    """
    columns = ColumnTransformer([
        ("num", Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]), [*NUTRIENTS, *DERIVED]),
        ("opt", Pipeline([
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler()),
        ]), list(OPTIONAL)),
        ("cat", Pipeline([
            ("imputer", SimpleImputer(strategy="constant", fill_value="unknown")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", min_frequency=min_frequency,
                                     sparse_output=False)),
        ]), list(CATEGORICAL)),
    ])
    return Pipeline([
        ("derive", FunctionTransformer(add_derived_features, feature_names_out=_derived_names)),
        ("columns", columns),
    ])


def make_model(estimator, **preparation_options) -> Pipeline:
    """Un seul objet : préparation commune puis modèle."""
    return Pipeline([("preparation", preparation(**preparation_options)), ("model", estimator)])


class FlatClassifier(ClassifierMixin, BaseEstimator):
    """
    Enveloppe qui aplatit les prédictions en entiers de forme (n,). CatBoost multiclasse
    renvoie une forme (n, 1) que NumPy diffuse en silence : les métriques deviennent
    fausses sans erreur. À utiliser autour de `CatBoostClassifier`.
    """

    def __init__(self, estimator=None):
        self.estimator = estimator

    def fit(self, X, y, **fit_params):
        self.estimator_ = clone(self.estimator).fit(X, y, **fit_params)
        self.classes_ = np.unique(y)
        return self

    def predict(self, X):
        return np.asarray(self.estimator_.predict(X)).ravel().astype(int)

    def predict_proba(self, X):
        return self.estimator_.predict_proba(X)


# ============================================================================
# ÉVALUATION
# ============================================================================

def make_cv(n_splits: int = N_FOLDS, seed: int = RANDOM_SEED) -> StratifiedKFold:
    """Les plis communs : stratifiés, mélangés, graine fixée. Mêmes indices à chaque appel."""
    return StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)


def cross_validate_models(models: dict, X: pd.DataFrame, y, cv=None, n_jobs: int | None = -1
                          ) -> pd.DataFrame:
    """
    Validation croisée de chaque modèle sur les mêmes plis et les mêmes métriques (à
    appeler sur le train uniquement). Une ligne par modèle : moyenne et écart-type de
    chaque métrique, temps moyens d'ajustement et de prédiction par pli.
    """
    cv = make_cv() if cv is None else cv
    rows = []
    for name, model in models.items():
        scores = cross_validate(model, X, y, cv=cv, scoring=SCORING, n_jobs=n_jobs)
        row = {"model": name}
        for metric in SCORING:
            row[f"{metric}_mean"] = scores[f"test_{metric}"].mean()
            row[f"{metric}_std"] = scores[f"test_{metric}"].std()
        row["fit_time_s"] = scores["fit_time"].mean()
        row["predict_time_s"] = scores["score_time"].mean()
        rows.append(row)
    return pd.DataFrame(rows).set_index("model")


def test_scores(model, X_test: pd.DataFrame, y_test) -> dict:
    """Métriques sur le test (modèle déjà ajusté sur tout le train) et latence par produit."""
    start = time.perf_counter()
    predictions = np.asarray(model.predict(X_test)).ravel()
    elapsed = time.perf_counter() - start
    return {
        "f1_macro_test": f1_score(y_test, predictions, average="macro"),
        "accuracy_test": accuracy_score(y_test, predictions),
        "balanced_accuracy_test": balanced_accuracy_score(y_test, predictions),
        "latency_ms_per_product": 1000 * elapsed / len(X_test),
    }


# pytest ne doit pas collecter `test_scores` comme un test quand le module est importé
test_scores.__test__ = False


def normalized_confusion(y_true, y_pred) -> pd.DataFrame:
    """Matrice de confusion normalisée par ligne (rappel par grade) : chaque ligne somme à 1."""
    matrix = confusion_matrix(y_true, y_pred, labels=range(len(GRADES)), normalize="true")
    return pd.DataFrame(matrix, index=pd.Index(GRADES, name="true"), columns=pd.Index(GRADES, name="predicted"))
