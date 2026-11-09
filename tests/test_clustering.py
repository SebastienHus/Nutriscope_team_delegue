"""
Tests pytest de la bibliothèque de segmentation — TP 16 (matinée).

Points vérifiés : les règles de plausibilité écartent les incohérences sans toucher aux
produits réels mais extrêmes ; l'imputation passe par la sous-catégorie avant la médiane
globale ; `log1p` ne vise que les colonnes asymétriques, choisies au `fit` puis figées ;
le préprocesseur rend une matrice complète et centrée ; le coude se lit sur les k
réellement testés ; `scan_k` mesure ce que le notebook affiche. Tout tourne sur de petits
jeux synthétiques.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError

from nutriscope.clustering import (
    CLUSTER_FEATURES,
    FIBER,
    GroupMedianImputer,
    SkewedLog1p,
    cluster_deviations,
    elbow_k,
    implausible_mask,
    make_preprocessor,
    plausibility_flags,
    scan_k,
)


def product(**overrides) -> dict:
    """Un produit plausible (biscuit), modifiable champ par champ."""
    base = {
        "pnns_groups_1": "Sugary snacks", "pnns_groups_2": "Biscuits and cakes",
        "energy-kcal_100g": 480.0, "fat_100g": 20.0, "saturated-fat_100g": 10.0,
        "carbohydrates_100g": 65.0, "sugars_100g": 30.0, "proteins_100g": 6.0,
        "salt_100g": 0.5, FIBER: 3.0,
    }
    return {**base, **overrides}


@pytest.fixture
def catalog() -> pd.DataFrame:
    """Deux familles bien séparées et une sous-catégorie sans fibres connues."""
    rng = np.random.default_rng(0)
    rows = []
    for _ in range(40):
        rows.append(product(sugars_100g=rng.uniform(25, 35), fat_100g=rng.uniform(15, 25),
                            **{FIBER: rng.uniform(2, 4)}))
        rows.append(product(pnns_groups_1="Beverages", pnns_groups_2="Fruit juices",
                            **{"energy-kcal_100g": rng.uniform(40, 50), "fat_100g": 0.0,
                               "saturated-fat_100g": 0.0, "carbohydrates_100g": 10.0,
                               "sugars_100g": rng.uniform(8, 10), "proteins_100g": 0.5,
                               "salt_100g": 0.01, FIBER: rng.uniform(0, 0.4)}))
    rows.append(product(pnns_groups_2="Sweets", **{FIBER: np.nan}))
    return pd.DataFrame(rows)


# ============================================================================
# VALEURS IMPOSSIBLES
# ============================================================================

def test_plausible_product_passes():
    assert not implausible_mask(pd.DataFrame([product()])).any()


@pytest.mark.parametrize("overrides, rule", [
    ({"fat_100g": 60.0, "carbohydrates_100g": 50.0}, "mass_over_100g"),
    ({"energy-kcal_100g": 950.0}, "energy_over_max"),
    ({"saturated-fat_100g": 25.0}, "saturated_over_fat"),
    ({"sugars_100g": 70.0}, "sugars_over_carbs"),
    ({"pnns_groups_1": "Beverages", "fat_100g": 0.0, "saturated-fat_100g": 0.0,
      "carbohydrates_100g": 11.0, "sugars_100g": 10.0, "proteins_100g": 0.0, "salt_100g": 12.0},
     "beverage_salt_over_seawater"),
])
def test_each_rule_flags_its_case(overrides, rule):
    flags = plausibility_flags(pd.DataFrame([product(**overrides)]))
    assert flags.loc[0, rule]
    assert flags.loc[0].sum() == 1, "a single inconsistency should trigger a single rule"


def test_rounding_tolerance_keeps_pure_oil():
    oil = product(**{"energy-kcal_100g": 900.0, "fat_100g": 100.0, "saturated-fat_100g": 15.0,
                     "carbohydrates_100g": 0.5, "sugars_100g": 0.5, "proteins_100g": 0.5,
                     "salt_100g": 0.01})
    assert not implausible_mask(pd.DataFrame([oil])).any()


def test_fiber_not_counted_twice_in_mass():
    # Étiquetage américain : les 12 g de fibres sont déjà dans les 80 g de glucides
    cereal = product(**{"fat_100g": 5.0, "saturated-fat_100g": 1.0, "carbohydrates_100g": 80.0,
                        "proteins_100g": 10.0, FIBER: 12.0})
    assert not implausible_mask(pd.DataFrame([cereal])).any()


def test_salty_product_outside_beverages_is_kept():
    stock_cube = product(pnns_groups_1="Fat and sauces", pnns_groups_2="Dressings and sauces",
                         salt_100g=50.0, carbohydrates_100g=20.0, sugars_100g=5.0)
    assert not implausible_mask(pd.DataFrame([stock_cube])).any()


def test_missing_values_trigger_no_rule():
    flags = plausibility_flags(pd.DataFrame([product(**{c: np.nan for c in CLUSTER_FEATURES})]))
    assert not flags.any(axis=None)


# ============================================================================
# TRANSFORMATEURS
# ============================================================================

def test_group_median_imputer_uses_group_then_global():
    df = pd.DataFrame({
        "group": ["a", "a", "a", "b", "b", None, "c"],
        "x": [1.0, 3.0, np.nan, 10.0, np.nan, np.nan, np.nan],
    })
    out = GroupMedianImputer(["x"], "group").fit(df).transform(df)
    assert out.loc[2, "x"] == 2.0           # médiane du groupe a
    assert out.loc[4, "x"] == 10.0          # médiane du groupe b
    assert out.loc[5, "x"] == 3.0           # groupe manquant : médiane globale (1, 3, 10)
    assert out.loc[6, "x"] == 3.0           # groupe sans valeur : médiane globale
    assert df["x"].isna().sum() == 4, "transform must not modify its input"


def test_group_median_imputer_falls_back_for_unseen_group():
    train = pd.DataFrame({"group": ["a", "a"], "x": [1.0, 3.0]})
    new = pd.DataFrame({"group": ["z"], "x": [np.nan]})
    assert GroupMedianImputer(["x"], "group").fit(train).transform(new).loc[0, "x"] == 2.0


def test_group_median_imputer_requires_fit():
    with pytest.raises(NotFittedError):
        GroupMedianImputer(["x"], "group").transform(pd.DataFrame({"group": ["a"], "x": [1.0]}))


def test_skewed_log1p_targets_skewed_columns_only():
    df = pd.DataFrame({"flat": np.linspace(0, 10, 50), "skewed": [0.0] * 45 + [50.0, 60, 80, 90, 100]})
    step = SkewedLog1p(["flat", "skewed"], threshold=1.0).fit(df)
    assert step.log_cols_ == ["skewed"]
    out = step.transform(df)
    np.testing.assert_allclose(out["skewed"], np.log1p(df["skewed"]))
    np.testing.assert_allclose(out["flat"], df["flat"])


def test_skewed_log1p_columns_are_frozen_at_fit():
    train = pd.DataFrame({"x": [0.0] * 45 + [50.0, 60, 80, 90, 100]})
    step = SkewedLog1p(["x"]).fit(train)
    new = pd.DataFrame({"x": [5.0, 5.0, 5.0]})            # aucune asymétrie
    np.testing.assert_allclose(step.transform(new)["x"], np.log1p(5.0))


def test_preprocessor_outputs_complete_standardized_matrix(catalog):
    X = make_preprocessor().fit_transform(catalog)
    assert X.shape == (len(catalog), len(CLUSTER_FEATURES))
    assert not np.isnan(X).any()
    np.testing.assert_allclose(X.mean(axis=0), 0, atol=1e-9)


def test_preprocessor_ignores_extra_columns(catalog):
    with_extra = catalog.assign(product_name="x", nutriscore_grade="c")
    np.testing.assert_allclose(make_preprocessor().fit_transform(with_extra),
                               make_preprocessor().fit_transform(catalog))


# ============================================================================
# CHOIX DE k
# ============================================================================

def test_elbow_on_tested_ks():
    ks, inertia = range(2, 9), [1000, 600, 300, 250, 230, 220, 215]
    assert elbow_k(ks, inertia) == 4


def test_elbow_follows_the_x_axis():
    # Même courbe, axe décalé d'un cran : le k lu change d'autant
    assert elbow_k(range(1, 8), [1000, 600, 300, 250, 230, 220, 215]) == 3


def test_elbow_rejects_inconsistent_input():
    with pytest.raises(ValueError):
        elbow_k(range(2, 5), [10.0, 5.0])


def test_scan_k_reports_metrics_per_k(catalog):
    X = make_preprocessor().fit_transform(catalog)
    scan, models = scan_k(X, range(2, 5), seed=0)
    assert list(scan.index) == [2, 3, 4]
    assert set(models) == {2, 3, 4}
    assert scan["inertia"].is_monotonic_decreasing
    assert np.isnan(scan.loc[2, "inertia_gain_pct"])
    assert (scan["min_cluster_size"] >= 1).all()
    # Deux familles bien séparées : k = 2 les retrouve, avec une silhouette élevée
    assert scan.loc[2, "silhouette"] > 0.5
    assert sorted(np.bincount(models[2].labels_)) == [40, 41]


def test_cluster_deviations_sign():
    df = pd.DataFrame({"sugars_100g": [1.0, 1.0, 50.0, 50.0]})
    dev = cluster_deviations(df, [0, 0, 1, 1], ["sugars_100g"])
    assert dev.loc[0, "sugars_100g"] < 0 < dev.loc[1, "sugars_100g"]
