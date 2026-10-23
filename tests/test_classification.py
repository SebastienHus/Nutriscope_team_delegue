"""
Tests pytest de la bibliothèque de classification — TP 14 et TP 15.

Points de contrôle du TP 14 rendus exécutables : le préparateur n'a pas vu le test (3),
le nombre de colonnes en sortie (4), la matrice normalisée par ligne (5), des plis
identiques d'un modèle à l'autre (6), et la fuite `nutriscore_score` qui ne peut pas
revenir par accident (4c). Les tests tournent sur un petit jeu synthétique ; seul le
comptage des colonnes lit le jeu ML partagé.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.dummy import DummyClassifier

from nutriscope.classification import (
    CATEGORICAL,
    DERIVED,
    FEATURES,
    FORBIDDEN_FEATURES,
    GRADES,
    NUTRIENTS,
    OPTIONAL,
    SPLIT,
    TARGET,
    FlatClassifier,
    add_derived_features,
    dataset_path,
    decode_grades,
    encode_grades,
    load_dataset,
    make_cv,
    make_model,
    normalized_confusion,
    preparation,
    split_frame,
)


@pytest.fixture
def frame() -> pd.DataFrame:
    """Jeu synthétique au format du jeu ML : 13 features, cible, split, colonnes interdites."""
    rng = np.random.default_rng(0)
    n = 600
    df = pd.DataFrame({column: rng.uniform(0, 30, n) for column in NUTRIENTS})
    df["energy-kcal_100g"] = rng.uniform(1, 600, n)
    df["fiber_100g"] = np.where(rng.random(n) < 0.4, np.nan, rng.uniform(0, 10, n))
    df["fruits-vegetables-legumes_100g"] = np.where(rng.random(n) < 0.4, np.nan, rng.uniform(0, 100, n))
    df["nova_group"] = pd.array(np.where(rng.random(n) < 0.4, None, rng.integers(1, 5, n)), dtype="Int64")
    df["additives_n"] = pd.array(np.where(rng.random(n) < 0.4, None, rng.integers(0, 8, n)), dtype="Int64")
    df["pnns_groups_1"] = rng.choice(["Sugary snacks", "Beverages", "Fish Meat Eggs"], n)
    df["pnns_groups_2"] = rng.choice(["Sweets", "Sodas", "Meat", "Rare aisle"], n, p=[0.4, 0.3, 0.29, 0.01])
    df[TARGET] = rng.choice(list(GRADES), n)
    df[SPLIT] = np.where(rng.random(n) < 0.2, "test", "train")
    df["code"] = [f"{i:013d}" for i in range(n)]
    df["nutriscore_score"] = rng.integers(-15, 40, n)
    return df


def test_features_contain_no_forbidden_column():
    assert len(FEATURES) == 13
    assert not set(FEATURES) & set(FORBIDDEN_FEATURES)


def test_nutriscore_score_cannot_come_back_as_a_feature(frame):
    with pytest.raises(ValueError, match="nutriscore_score"):
        split_frame(frame, features=[*FEATURES, "nutriscore_score"])


def test_split_frame_follows_the_frozen_split_column(frame):
    X_train, X_test, y_train, y_test = split_frame(frame)
    assert len(X_train) == (frame[SPLIT] == "train").sum() == len(y_train)
    assert len(X_test) == (frame[SPLIT] == "test").sum() == len(y_test)
    assert list(X_train.columns) == list(FEATURES)


def test_grades_are_encoded_in_a_fixed_order():
    assert list(encode_grades(["a", "e", "c"])) == [0, 4, 2]
    assert list(decode_grades(encode_grades(list(GRADES)))) == list(GRADES)
    with pytest.raises(ValueError):
        encode_grades(["z"])


def test_derived_features_are_pure_and_safe_on_zero(frame):
    X = frame[list(FEATURES)].copy()
    X.loc[X.index[0], "carbohydrates_100g"] = 0.0
    before = X.copy()
    out = add_derived_features(X)
    pd.testing.assert_frame_equal(X, before)
    assert list(out.columns) == [*FEATURES, *DERIVED]
    assert out.loc[out.index[0], "ratio_sugars_carbs"] == 0.0
    assert out[list(DERIVED)].notna().all().all()


def test_preparation_has_not_seen_the_test(frame):
    """Point de contrôle 3 : ajusté sur le train, le train standardisé est centré, pas le test."""
    X_train, X_test, _, _ = split_frame(frame)
    shifted_test = X_test.assign(**{"sugars_100g": X_test["sugars_100g"] + 50})
    prep = preparation().fit(X_train)
    column = list(prep.get_feature_names_out()).index("num__sugars_100g")
    assert abs(prep.transform(X_train)[:, column].mean()) < 1e-9
    assert abs(prep.transform(shifted_test)[:, column].mean()) > 1e-3


def test_rare_categories_are_grouped(frame):
    X_train, _, _, _ = split_frame(frame)
    names = list(preparation().fit(X_train).get_feature_names_out())
    assert "cat__pnns_groups_2_Rare aisle" not in names
    assert any(name.startswith("cat__pnns_groups_2_infrequent") for name in names)


def test_preparation_outputs_about_sixty_columns():
    """Point de contrôle 4, sur le jeu ML partagé : une soixantaine de colonnes, pas des centaines."""
    try:
        df = load_dataset(dataset_path())
    except FileNotFoundError as error:
        pytest.skip(str(error))
    X_train, _, _, _ = split_frame(df)
    width = preparation().fit_transform(X_train).shape[1]
    assert 40 <= width <= 90, width


def test_folds_are_identical_from_one_call_to_the_next(frame):
    """Point de contrôle 6."""
    X_train, _, y_train, _ = split_frame(frame)
    first = [test for _, test in make_cv().split(X_train, y_train)]
    second = [test for _, test in make_cv().split(X_train, y_train)]
    assert all(np.array_equal(a, b) for a, b in zip(first, second, strict=True))


def test_normalized_confusion_sums_to_one_by_row():
    """Point de contrôle 5 : normalisé par ligne (rappel), pas par colonne."""
    y_true = np.array([0, 0, 1, 1, 2, 3, 4, 4])
    y_pred = np.array([0, 1, 1, 1, 3, 3, 4, 3])
    matrix = normalized_confusion(y_true, y_pred)
    present = matrix.index[[0, 1, 2, 3, 4]]
    assert np.allclose(matrix.loc[present].sum(axis=1), 1.0)
    assert list(matrix.columns) == list(GRADES)


class _ColumnPredictions(ClassifierMixin, BaseEstimator):
    """Imite CatBoost multiclasse : prédictions de forme (n, 1)."""

    def fit(self, X, y):
        self.classes_ = np.unique(y)
        return self

    def predict(self, X):
        return np.zeros((len(X), 1))


def test_flat_classifier_flattens_column_predictions(frame):
    X_train, X_test, y_train, _ = split_frame(frame)
    model = make_model(FlatClassifier(_ColumnPredictions())).fit(X_train, y_train)
    predictions = model.predict(X_test)
    assert predictions.shape == (len(X_test),)
    assert predictions.dtype.kind == "i"


def test_make_model_runs_end_to_end(frame):
    X_train, X_test, y_train, _ = split_frame(frame)
    model = make_model(DummyClassifier(strategy="most_frequent")).fit(X_train, y_train)
    assert model.predict(X_test).shape == (len(X_test),)
    assert set(CATEGORICAL) <= set(X_train.columns) and set(OPTIONAL) <= set(X_train.columns)
