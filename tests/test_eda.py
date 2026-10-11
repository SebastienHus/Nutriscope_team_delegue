"""
Tests pytest des fonctions de calcul de l'analyse exploratoire — TP 10.

Chaque test construit un petit jeu synthétique dont le résultat se calcule à la main :
valeurs connues, groupe trop petit écarté, résultat vide bien formé, et pureté (le
DataFrame reçu n'est jamais modifié).
"""

import numpy as np
import pandas as pd
import pytest

from eda import (
    business_inconsistencies,
    cohens_d,
    compare_by_group,
    compare_two_groups,
    completeness_by_group,
    correlations_by_group,
    correlations_with_target,
    cramers_v,
    exclude_unknown,
    grade_crosstab,
    main_brand,
    profile_by_group,
    redundant_pairs,
    remaining_extremes,
    robust_zscore,
    univariate_profile,
)

NUTRIENTS_ROW = {  # produit cohérent : 4 × 10 + 4 × 50 + 9 × 10 = 330 kcal
    "energy-kcal_100g": 330.0, "fat_100g": 10.0, "saturated-fat_100g": 2.0,
    "carbohydrates_100g": 50.0, "sugars_100g": 5.0, "proteins_100g": 10.0,
    "salt_100g": 1.0, "sodium_100g": 0.4,
}


def products(n: int, group: str = "A", **overrides) -> pd.DataFrame:
    """`n` produits cohérents du groupe `group`, avec des colonnes éventuellement remplacées."""
    rows = pd.DataFrame([NUTRIENTS_ROW] * n)
    rows["pnns_groups_1"] = group
    rows["nutriscore_grade"] = "c"
    for column, value in overrides.items():
        rows[column] = value
    return rows


# ============================================================================
# PÉRIMÈTRE ET DISTRIBUTIONS
# ============================================================================

def test_exclude_unknown_drops_unknown_and_missing_groups():
    df = pd.DataFrame({"pnns_groups_1": ["A", "unknown", None, "B"]})
    assert exclude_unknown(df)["pnns_groups_1"].tolist() == ["A", "B"]


def test_univariate_profile_known_values():
    profile = univariate_profile(pd.Series([1.0, 2.0, 3.0, 4.0, 5.0, np.nan]))
    assert profile["n"] == 5
    assert profile["missing_pct"] == pytest.approx(100 / 6)
    assert profile["median"] == 3.0
    assert profile["mean"] == 3.0
    assert profile["iqr"] == 2.0       # q75 = 4, q25 = 2
    assert profile["mad"] == 1.0       # écarts à 3 : 2, 1, 0, 1, 2
    assert profile["min"] == 1.0 and profile["max"] == 5.0


def test_univariate_profile_cv_is_nan_when_mean_is_zero():
    assert np.isnan(univariate_profile(pd.Series([-1.0, 1.0]))["cv"])


def test_profile_by_group_excludes_and_lists_small_groups():
    df = pd.concat([products(30, "A"), products(5, "B")], ignore_index=True)
    df.loc[:9, "sugars_100g"] = np.nan              # 10 sucres manquants dans A

    table, excluded = profile_by_group(df, ["sugars_100g", "salt_100g"], min_n=30)

    assert table.index.tolist() == ["A"]
    assert excluded.to_dict() == {"B": 5}
    assert table.loc["A", ("sugars_100g", "n")] == 20
    assert table.loc["A", ("sugars_100g", "median")] == 5.0
    assert table.columns.get_level_values(0).unique().tolist() == ["sugars_100g", "salt_100g"]


# ============================================================================
# ASSOCIATION RAYON × GRADE
# ============================================================================

def test_grade_crosstab_keeps_only_grades_a_to_e():
    df = pd.DataFrame({"pnns_groups_1": ["A", "A", "B", "B"],
                       "nutriscore_grade": ["a", "unknown", "e", "not-applicable"]})
    counts = grade_crosstab(df)
    assert counts.columns.tolist() == ["a", "b", "c", "d", "e"]
    assert counts.to_numpy().sum() == 2


def test_cramers_v_is_one_for_perfect_association_and_zero_for_independence():
    perfect = pd.DataFrame([[50, 0], [0, 50]])
    independent = pd.DataFrame([[25, 25], [25, 25]])
    assert cramers_v(perfect) == pytest.approx(1.0)
    assert cramers_v(independent) == pytest.approx(0.0)


def test_cramers_v_ignores_empty_rows():
    counts = pd.DataFrame([[40, 10], [10, 40], [0, 0]])
    assert cramers_v(counts) == pytest.approx(0.6)   # khi-deux = 36, n = 100, k = 1


def test_cramers_v_differs_on_a_row_normalized_table():
    # Normaliser par ligne donne le même poids à chaque groupe, quel que soit son effectif :
    # le V obtenu n'est plus celui des données (d'où l'exigence d'un tableau en effectifs).
    counts = pd.DataFrame([[80, 20], [10, 10]])
    row_pct = counts.div(counts.sum(axis=1), axis=0)
    assert cramers_v(counts) == pytest.approx(0.2582, rel=1e-3)
    assert cramers_v(row_pct) != pytest.approx(cramers_v(counts), rel=1e-2)


# ============================================================================
# COMPLÉTUDE ET INCOHÉRENCES
# ============================================================================

def test_completeness_by_group_exact_rates():
    df = pd.concat([products(20, "A"), products(10, "B")], ignore_index=True)
    df.loc[:4, "sugars_100g"] = np.nan                 # 5 / 20 sucres manquants dans A
    df.loc[5:9, "nutriscore_grade"] = np.nan           # 5 / 20 grades manquants dans A

    table = completeness_by_group(df, "pnns_groups_1", columns=["sugars_100g", "salt_100g"], min_n=20)

    assert table.index.tolist() == ["A"]               # B (10 produits) écarté
    assert table.loc["A", "n"] == 20
    assert table.loc["A", "sugars_100g"] == 75.0
    assert table.loc["A", "salt_100g"] == 100.0
    assert table.loc["A", "complete_pct"] == 75.0
    assert table.loc["A", "score_pct"] == 75.0


def test_completeness_by_group_raises_without_any_known_column():
    with pytest.raises(ValueError):
        completeness_by_group(products(20), "pnns_groups_1", columns=["absent_100g"])


def test_main_brand_keeps_first_brand():
    brands = pd.Series(["Carrefour, Carrefour Bio", " Auchan ", "", None])
    assert main_brand(brands).tolist()[:2] == ["Carrefour", "Auchan"]
    assert main_brand(brands).iloc[2:].isna().all()


def test_business_inconsistencies_raise_one_flag_per_broken_rule():
    df = products(6)
    df.loc[1, "sugars_100g"] = 60.0                    # sucres > glucides
    df.loc[2, "saturated-fat_100g"] = 12.0             # saturés > lipides
    df.loc[3, "sodium_100g"] = 1.0                     # sel ≠ 2,5 × sodium
    df.loc[4, "energy-kcal_100g"] = 600.0              # 270 kcal d'écart au calcul 4 / 4 / 9
    df.loc[5, "energy-kcal_100g"] = 0.0                # énergie nulle avec macronutriments

    flags = business_inconsistencies(df)

    assert flags.dtypes.eq(bool).all()
    assert not flags.loc[0].any()                      # produit cohérent : aucun drapeau
    assert flags.loc[1, "sugars_over_carbohydrates"]
    assert flags.loc[2, "saturated_over_fat"]
    assert flags.loc[3, "salt_sodium_mismatch"]
    assert flags.loc[4, "energy_gap"]
    assert flags.loc[5, "zero_energy_with_macros"]
    assert flags.sum().tolist() == [1, 1, 1, 2, 1]     # la ligne 5 est aussi à 330 kcal d'écart


def test_business_inconsistencies_never_flag_missing_values():
    df = products(1)
    df.loc[0, ["sugars_100g", "sodium_100g", "energy-kcal_100g"]] = np.nan
    assert not business_inconsistencies(df).loc[0].any()


# ============================================================================
# CORRÉLATIONS
# ============================================================================

def test_pearson_is_one_on_a_linear_relation():
    x = np.arange(50, dtype=float)
    df = pd.DataFrame({"x": x, "score": 2 * x + 1})
    assert correlations_with_target(df, ["x"], "score").loc["x", "pearson"] == pytest.approx(1.0)


def test_spearman_is_one_on_a_monotone_relation_where_pearson_is_not():
    x = np.arange(50, dtype=float)
    df = pd.DataFrame({"x": x, "score": np.exp(x / 5)})
    table = correlations_with_target(df, ["x"], "score")
    assert table.loc["x", "spearman"] == pytest.approx(1.0)
    assert table.loc["x", "pearson"] < 0.9


def test_correlations_sorted_by_absolute_spearman_and_skip_small_samples():
    rng = np.random.default_rng(42)
    x = rng.normal(size=100)
    df = pd.DataFrame({"weak": x + rng.normal(scale=3, size=100), "strong_neg": -x,
                       "sparse": [1.0] * 10 + [np.nan] * 90, "score": x})
    table = correlations_with_target(df, ["weak", "strong_neg", "sparse"], "score", min_n=30)
    assert table.index.tolist() == ["strong_neg", "weak"]   # signe gardé, « sparse » omis
    assert table.loc["strong_neg", "spearman"] == pytest.approx(-1.0)
    assert table.loc["strong_neg", "n"] == 100


def test_correlations_are_empty_but_well_formed_when_nothing_is_computable():
    table = correlations_with_target(pd.DataFrame({"x": [1.0], "score": [2.0]}), ["x"], "score")
    assert table.empty and table.columns.tolist() == ["n", "pearson", "spearman"]


def test_correlations_by_group_omit_groups_under_the_threshold():
    x = np.arange(40, dtype=float)
    df = pd.concat([pd.DataFrame({"pnns_groups_1": "A", "x": x, "score": x}),
                    pd.DataFrame({"pnns_groups_1": "B", "x": x[:10], "score": x[:10]})])
    table = correlations_by_group(df, ["x"], "score", min_n=30)
    assert table["pnns_groups_1"].tolist() == ["A"]
    assert table.columns.tolist() == ["pnns_groups_1", "column", "n", "pearson", "spearman"]
    assert table["spearman"].dtype == float          # le groupe B vide ne dégrade pas le type


def test_redundant_pairs_detect_salt_and_sodium():
    rng = np.random.default_rng(42)
    sodium = rng.uniform(0, 2, size=200)
    df = pd.DataFrame({"salt_100g": sodium * 2.5, "sodium_100g": sodium,
                       "sugars_100g": rng.uniform(0, 50, size=200)})
    pairs = redundant_pairs(df.corr(method="spearman"), threshold=0.8)
    assert len(pairs) == 1
    assert set(pairs.loc[0, ["var_1", "var_2"]]) == {"salt_100g", "sodium_100g"}
    assert pairs.loc[0, "rho"] == pytest.approx(1.0)


# ============================================================================
# VALEURS EXTRÊMES
# ============================================================================

def test_robust_zscore_known_values():
    z = robust_zscore(pd.Series([1.0, 2.0, 3.0, 4.0, 100.0]))
    # médiane 3, MAD 1 → échelle 1,4826
    assert z.iloc[2] == 0.0
    assert z.iloc[4] == pytest.approx(97 / 1.4826, rel=1e-3)


def test_robust_zscore_falls_back_when_mad_is_zero():
    s = pd.Series([0.0] * 20 + [30.0])                # MAD = 0 : boissons sans lipides
    z = robust_zscore(s)
    assert np.isfinite(z).all()
    assert z.iloc[:20].eq(0).all() and z.iloc[20] > 3.5
    assert robust_zscore(pd.Series([5.0] * 10)).isna().all()   # série constante : aucun extrême


def test_remaining_extremes_detect_intruders_in_their_own_group_both_ways():
    rng = np.random.default_rng(42)
    salty = pd.DataFrame({"pnns_groups_1": "Salty", "salt_100g": rng.normal(2.0, 0.2, 50)})
    drinks = pd.DataFrame({"pnns_groups_1": "Drinks", "salt_100g": rng.normal(0.05, 0.01, 50)})
    drinks.loc[0, "salt_100g"] = 2.0                  # banal ailleurs, extrême dans son rayon
    salty.loc[0, "salt_100g"] = 0.0                   # extrême par le bas
    df = pd.concat([salty, drinks], ignore_index=True)
    df["code"] = [f"{i:013d}" for i in range(len(df))]

    extremes = remaining_extremes(df, ["salt_100g"], threshold=3.5)

    assert {0, 50} <= set(extremes.index)
    assert extremes["z"].abs().is_monotonic_decreasing
    assert extremes.loc[50, "pnns_groups_1"] == "Drinks" and extremes.loc[50, "z"] > 0
    assert extremes.loc[0, "z"] < 0


def test_remaining_extremes_empty_result_is_well_formed():
    df = pd.DataFrame({"code": ["1", "2", "3"], "pnns_groups_1": "A", "salt_100g": [1.0, 1.0, 1.0]})
    extremes = remaining_extremes(df, ["salt_100g"])
    assert extremes.empty
    assert extremes.columns.tolist() == ["code", "pnns_groups_1", "nutrient", "value",
                                         "group_median", "z"]


# ============================================================================
# HYPOTHÈSES
# ============================================================================

def test_cohens_d_known_value_and_degenerate_cases():
    a = pd.Series([1.0, 2.0, 3.0])
    b = pd.Series([3.0, 4.0, 5.0])                    # écart des moyennes 2, écart-type combiné 1
    assert cohens_d(a, b) == pytest.approx(2.0)
    assert np.isnan(cohens_d(pd.Series([1.0, 1.0]), pd.Series([1.0, 1.0])))
    assert np.isnan(cohens_d(pd.Series([1.0]), b))


def test_compare_two_groups_reports_counts_medians_and_test():
    result = compare_two_groups(pd.Series([1.0, 2.0, 3.0, np.nan]), pd.Series([10.0, 11.0, 12.0]))
    assert (result["n_a"], result["n_b"]) == (3, 3)
    assert result["median_diff"] == 9.0
    assert 0 < result["p_value"] < 0.2


def test_compare_by_group_is_stratified_and_skips_small_strata():
    df = pd.concat([
        pd.DataFrame({"pnns_groups_1": "A", "nutriscore_grade": ["a"] * 10 + ["e"] * 10,
                      "sugars_100g": [1.0] * 10 + [20.0] * 10}),
        pd.DataFrame({"pnns_groups_1": "B", "nutriscore_grade": ["a"] * 3 + ["e"] * 10,
                      "sugars_100g": [1.0] * 13}),
    ])
    table = compare_by_group(df, "sugars_100g", "nutriscore_grade", "a", "e", min_n=10)
    assert table.index.tolist() == ["A"]
    assert table.loc["A", "median_diff"] == 19.0


# ============================================================================
# PURETÉ
# ============================================================================

def test_functions_do_not_modify_their_input():
    df = pd.concat([products(30, "A"), products(30, "B")], ignore_index=True)
    df["nutriscore_score"] = np.arange(60, dtype=float)
    df["sugars_100g"] = np.arange(60, dtype=float) % 7
    df["code"] = df.index.astype(str)
    before = df.copy()

    profile_by_group(df, ["sugars_100g"])
    completeness_by_group(df, "pnns_groups_1")
    business_inconsistencies(df)
    correlations_by_group(df, ["sugars_100g"], "nutriscore_score")
    remaining_extremes(df, ["salt_100g"])

    pd.testing.assert_frame_equal(df, before)
