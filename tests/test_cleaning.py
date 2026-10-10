"""
Tests pytest du module de nettoyage — TP 9.

Pour chaque règle : un test nominal (la règle fait ce que dit sa docstring, le compte
rendu compte juste), des cas tordus relevés au TP 2 (la valeur impossible est traitée,
la valeur voisine légitime ne l'est pas), la pureté (entrée intacte) et l'idempotence
sur l'échantillon réel (second passage identique, zéro ligne touchée).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import schema
from cleaning import (
    CLEANING_RULES,
    DEFAULT_STRATEGY,
    Report,
    apply_missing_strategy,
    bound_nutrients,
    clean,
    deduplicate_codes,
    filter_codes,
    fix_energy,
    handle_empty_categories,
    normalize_texts,
    normalize_units,
    type_columns,
    validate_output,
)

SAMPLE_PATH = Path(__file__).parent.parent / "data-nutriscope" / "echantillon_france.csv"
ALL_RULES = (*CLEANING_RULES, apply_missing_strategy)


# ============================================================================
# FIXTURES
# ============================================================================

BASE_PRODUCT = {
    "code": "3017620422003",
    "product_name": "Biscuit",
    "brands": "Marque",
    "categories_tags": "en:snacks,en:biscuits",
    "main_category": "en:biscuits",
    "pnns_groups_1": "Sugary snacks",
    "pnns_groups_2": "Biscuits and cakes",
    "nutriscore_grade": "d",
    "environmental_score_grade": "c",
    "energy-kcal_100g": 322.0,       # 8 × 4 + 50 × 4 + 10 × 9
    "energy_100g": 1347.25,
    "fat_100g": 10.0,
    "saturated-fat_100g": 2.0,
    "carbohydrates_100g": 50.0,
    "sugars_100g": 10.0,
    "fiber_100g": 3.0,
    "proteins_100g": 8.0,
    "salt_100g": 1.0,
    "sodium_100g": 0.4,
    "fruits-vegetables-legumes_100g": np.nan,
    "completeness": 0.8,
    "created_t": 1_600_000_000,       # 2020-09-13
    "last_modified_t": 1_700_000_000,
}


def make_products(*overrides: dict) -> pd.DataFrame:
    """DataFrame de produits sains, chacun modifié par son dictionnaire d'écarts."""
    return pd.DataFrame([{**BASE_PRODUCT, **override} for override in overrides])


@pytest.fixture
def tricky():
    """Un cas tordu par règle, tiré du TP 2."""
    return make_products(
        {"code": "3017620422003", "sugars_100g": 74_000.0},                          # 0 sucres impossibles
        {"code": "3274080005003", "energy-kcal_100g": 24_000.0, "energy_100g": 100_416.0},  # 1 énergie
        {"code": "3228857000166", "salt_100g": 5_000.0, "sodium_100g": 2_000.0},     # 2 sel impossible
        {"code": "3560 0700 48185"},                                                 # 3 code avec espaces
        {"code": "5449000000996", "completeness": 0.4},                              # 4 doublon peu complet
        {"code": "5449000000996", "completeness": 0.9},                              # 5 doublon complet
        {"code": "7622210449283", "product_name": "   ", "nutriscore_grade": "unknown"},  # 6 textes
        {"code": "3045140105502", "pnns_groups_1": np.nan, "categories_tags": np.nan,
         "main_category": np.nan},                                                   # 7 inclassable
        {"code": "8000500310427", **{c: np.nan for c in schema.KEY_NUTRIENTS},
         "energy_100g": np.nan, "sodium_100g": np.nan},                              # 8 sans nutriment
        {"code": "2000000151619"},                                                   # 9 code interne
        {"code": "30383354190402"},                                                  # 10 code à 14 chiffres
        {"code": "3017620425035", "fat_100g": 100.0, "saturated-fat_100g": 10.0,
         "carbohydrates_100g": 0.0, "sugars_100g": 0.0, "proteins_100g": 0.0,
         "energy-kcal_100g": 900.0, "energy_100g": 3765.6},                          # 11 900 kcal légitimes
        {"code": "3245990250203", "pnns_groups_1": "Alcoholic beverages",
         "energy-kcal_100g": 300.0, "energy_100g": 1255.2, "fat_100g": 0.0,
         "saturated-fat_100g": 0.0, "carbohydrates_100g": 30.0, "sugars_100g": 30.0,
         "proteins_100g": 0.0},                                                      # 12 liqueur
    )


@pytest.fixture(scope="module")
def sample():
    if not SAMPLE_PATH.exists():
        pytest.skip(f"Échantillon absent : {SAMPLE_PATH}")
    return pd.read_csv(SAMPLE_PATH, dtype={"code": str})


@pytest.fixture(scope="module")
def sample_inputs(sample):
    """Entrée de chaque règle sur l'échantillon : la sortie des règles qui la précèdent."""
    inputs, df = {}, sample
    for rule in ALL_RULES:
        inputs[rule.__name__] = df
        df, _ = rule(df)
    return inputs


# ============================================================================
# CONTRAT COMMUN : PURETÉ ET IDEMPOTENCE
# ============================================================================

@pytest.mark.parametrize("rule", ALL_RULES, ids=lambda rule: rule.__name__)
def test_rule_is_pure(rule, tricky):
    original = tricky.copy()
    df, report = rule(tricky)
    pd.testing.assert_frame_equal(tricky, original)
    assert isinstance(report, Report) and report.rule == rule.__name__


@pytest.mark.parametrize("rule", ALL_RULES, ids=lambda rule: rule.__name__)
def test_rule_is_idempotent(rule, sample_inputs):
    once, _ = rule(sample_inputs[rule.__name__])
    twice, report = rule(once)
    pd.testing.assert_frame_equal(once, twice)
    assert report.lines_changed == 0


# ============================================================================
# RÈGLE : TYPAGE
# ============================================================================

class TestTypeColumns:
    def test_types(self, tricky):
        df, report = type_columns(tricky)
        assert df["code"].map(type).eq(str).all()
        assert df["fat_100g"].dtype == "float64"
        assert df["created_t"].dt.year.iloc[0] == 2020    # timestamps Unix en secondes
        assert report.lines_before == report.lines_after == len(tricky)

    def test_unconvertible_value_counted(self):
        df, report = type_columns(make_products({"fat_100g": "abc"}, {}))
        assert pd.isna(df.loc[0, "fat_100g"])
        assert report.details["coerced_to_na"] == 1
        assert report.lines_changed == 1


# ============================================================================
# RÈGLE : TEXTES
# ============================================================================

class TestNormalizeTexts:
    def test_blank_name_and_unknown_grade(self, tricky):
        df, report = normalize_texts(tricky)
        assert pd.isna(df.loc[6, "product_name"])
        assert pd.isna(df.loc[6, "nutriscore_grade"])
        assert report.details["product_name_blank"] == 1
        assert report.details["nutriscore_grade_invalidated"] == 1

    def test_legitimate_grades_kept(self):
        products = make_products(
            {"nutriscore_grade": " A ", "environmental_score_grade": "a-plus"},
            {"nutriscore_grade": "not-applicable", "environmental_score_grade": "f"},
        )
        df, _ = normalize_texts(products)
        assert df["nutriscore_grade"].tolist() == ["a", "not-applicable"]
        assert df["environmental_score_grade"].tolist() == ["a-plus", "f"]


# ============================================================================
# RÈGLE : CODES
# ============================================================================

class TestFilterCodes:
    def test_spaces_removed(self, tricky):
        df, _ = filter_codes(tricky)
        assert df.loc[3, "code"] == "3560070048185"

    def test_unofficial_codes_removed(self, tricky):
        df, report = filter_codes(tricky)
        assert {9, 10}.isdisjoint(df.index)
        assert report.details["in_store_removed"] == 1
        assert report.details["invalid_length_removed"] == 1
        assert report.lines_after == len(tricky) - 2

    def test_missing_and_repeated_codes_removed(self):
        products = make_products({"code": np.nan}, {"code": "  "}, {"code": "00000000"}, {})
        df, report = filter_codes(products)
        assert df.index.tolist() == [3]
        assert report.details["missing_code_removed"] == 2
        assert report.details["invalid_length_removed"] == 1


# ============================================================================
# RÈGLE : DOUBLONS
# ============================================================================

class TestDeduplicateCodes:
    def test_keeps_most_complete(self, tricky):
        df, report = deduplicate_codes(tricky)
        assert 4 not in df.index and 5 in df.index
        assert report.details == {"duplicates_removed": 1, "duplicated_codes": 1}

    def test_tie_keeps_most_recent_and_preserves_order(self):
        products = make_products(
            {"code": "5449000000996", "last_modified_t": 1},
            {"code": "3017620422003"},
            {"code": "5449000000996", "last_modified_t": 2},
        )
        df, _ = deduplicate_codes(products)
        assert df.index.tolist() == [1, 2]


# ============================================================================
# RÈGLE : UNITÉS
# ============================================================================

class TestNormalizeUnits:
    def test_kcal_derived_from_kj(self):
        df, report = normalize_units(make_products({"energy-kcal_100g": np.nan, "energy_100g": 418.4}))
        assert df.loc[0, "energy-kcal_100g"] == pytest.approx(100.0)
        assert report.details["kcal_derived"] == 1

    def test_kcal_recalculated_when_ratio_out_of_range(self):
        products = make_products({"energy-kcal_100g": 74_000.0, "energy_100g": 2000.0}, {})
        df, report = normalize_units(products)
        assert df.loc[0, "energy-kcal_100g"] == pytest.approx(2000 / schema.KJ_PER_KCAL, abs=0.01)
        assert df.loc[1, "energy-kcal_100g"] == 322.0    # rapport 4,18 : plausible, inchangé
        assert report.details["kcal_recalculated"] == 1

    def test_eu_ratio_kept(self):
        """Facteurs de l'étiquetage européen : 4,2 kJ/kcal est légitime."""
        df, report = normalize_units(make_products({"energy-kcal_100g": 100.0, "energy_100g": 420.0}))
        assert df.loc[0, "energy-kcal_100g"] == 100.0
        assert report.details["kcal_recalculated"] == 0

    def test_salt_and_sodium(self):
        products = make_products(
            {"salt_100g": 2.5, "sodium_100g": np.nan},
            {"salt_100g": np.nan, "sodium_100g": 0.4},
            {"salt_100g": 1.0, "sodium_100g": 1.0},
        )
        df, report = normalize_units(products)
        assert df["sodium_100g"].tolist() == pytest.approx([1.0, 0.4, 0.4])
        assert df["salt_100g"].tolist() == pytest.approx([2.5, 1.0, 1.0])
        assert report.details["sodium_derived"] == 1
        assert report.details["salt_derived"] == 1
        assert report.details["sodium_recalculated"] == 1
        assert report.lines_changed == 3


# ============================================================================
# RÈGLE : BORNES
# ============================================================================

class TestBoundNutrients:
    def test_impossible_values_to_na(self, tricky):
        df, report = bound_nutrients(tricky)
        assert pd.isna(df.loc[0, "sugars_100g"])
        assert pd.isna(df.loc[2, "salt_100g"]) and pd.isna(df.loc[2, "sodium_100g"])
        assert report.details["sugars_100g_above_max"] == 1
        assert report.details["sodium_100g_above_max"] == 1

    def test_bounds_are_inclusive(self, tricky):
        df, _ = bound_nutrients(tricky)
        assert df.loc[11, "fat_100g"] == 100.0           # 100 g est à la borne, pas au-delà

    def test_negative_and_inconsistent_values(self):
        products = make_products(
            {"fat_100g": -5.0},
            {"sugars_100g": 60.0, "carbohydrates_100g": 50.0},
            {"sugars_100g": 50.4, "carbohydrates_100g": 50.0},   # dans la tolérance de 0,5 g
            {"saturated-fat_100g": 12.0, "fat_100g": 10.0},
        )
        df, report = bound_nutrients(products)
        assert pd.isna(df.loc[0, "fat_100g"])
        assert pd.isna(df.loc[1, "sugars_100g"])
        assert df.loc[2, "sugars_100g"] == 50.4
        assert pd.isna(df.loc[3, "saturated-fat_100g"])
        assert report.details["fat_100g_below_min"] == 1
        assert report.details["sugars_within_carbohydrates_invalidated"] == 1
        assert report.details["saturated_within_fat_invalidated"] == 1
        assert report.lines_changed == 3


# ============================================================================
# RÈGLE : ÉNERGIE
# ============================================================================

class TestFixEnergy:
    def test_over_max_recalculated(self, tricky):
        df, report = fix_energy(tricky)
        assert df.loc[1, "energy-kcal_100g"] == pytest.approx(322.0)
        assert df.loc[1, "energy_100g"] == pytest.approx(322.0 * schema.KJ_PER_KCAL, abs=0.01)
        assert report.details["over_max_recalculated"] == 1

    def test_max_kept_and_alcohol_exempted(self, tricky):
        df, _ = fix_energy(tricky)
        assert df.loc[11, "energy-kcal_100g"] == 900.0
        assert df.loc[12, "energy-kcal_100g"] == 300.0   # 120 kcal calculées, l'alcool n'est pas compté

    def test_over_max_without_macronutrients_invalidated(self):
        products = make_products({"energy-kcal_100g": 1000.0, "energy_100g": 4184.0,
                                  "proteins_100g": np.nan})
        df, report = fix_energy(products)
        assert pd.isna(df.loc[0, "energy-kcal_100g"]) and pd.isna(df.loc[0, "energy_100g"])
        assert report.details["over_max_invalidated"] == 1
        assert report.details["kj_invalidated"] == 1

    def test_zero_and_incoherent_recalculated(self):
        products = make_products(
            {"energy-kcal_100g": 0.0, "energy_100g": 0.0},
            {"energy-kcal_100g": 100.0, "energy_100g": 418.4},   # calcul : 322 kcal
        )
        df, report = fix_energy(products)
        assert df["energy-kcal_100g"].tolist() == pytest.approx([322.0, 322.0])
        assert report.details["missing_or_zero_recalculated"] == 1
        assert report.details["incoherent_recalculated"] == 1
        assert report.details["kj_realigned"] == 2


# ============================================================================
# RÈGLE : CATÉGORIES
# ============================================================================

class TestHandleEmptyCategories:
    def test_unclassifiable_removed(self, tricky):
        df, report = handle_empty_categories(tricky)
        assert 7 not in df.index
        assert report.details["unclassifiable_removed"] == 1
        assert report.details["pnns_groups_1_filled_unknown"] == 1

    def test_group_canonicalized_and_flag(self):
        products = make_products(
            {"pnns_groups_1": "sugary-snacks"},
            {"pnns_groups_1": "Pizza"},
            {"categories_tags": np.nan},
        )
        df, report = handle_empty_categories(products)
        assert df["pnns_groups_1"].tolist() == ["Sugary snacks", "unknown", "Sugary snacks"]
        assert df["empty_category"].tolist() == [False, False, True]
        assert report.details["pnns_groups_1_unrecognized"] == 1

    def test_main_category_from_last_tag(self):
        df, report = handle_empty_categories(make_products({"main_category": np.nan}))
        assert df.loc[0, "main_category"] == "en:biscuits"
        assert report.details["main_category_from_tags"] == 1


# ============================================================================
# RÈGLE : MANQUANTS
# ============================================================================

class TestApplyMissingStrategy:
    def test_default_strategy(self, tricky):
        df, report = apply_missing_strategy(tricky)
        assert 8 not in df.index
        assert df["fiber_100g_missing"].dtype == bool
        assert report.details["insufficient_key_nutrients_removed"] == 1
        assert report.lines_changed == 1      # les drapeaux ne comptent pas

    def test_constant_and_drop_column(self):
        products = make_products({"fiber_100g": np.nan}, {})
        strategy = {"fiber_100g": "constant:0", "brands": "drop_column"}
        df, report = apply_missing_strategy(products, strategy)
        assert df["fiber_100g"].tolist() == [0.0, 3.0]
        assert "brands" not in df.columns
        assert report.details["fiber_100g_filled"] == 1
        assert report.details["columns_dropped"] == 1

    def test_unknown_decision_raises(self, tricky):
        with pytest.raises(ValueError):
            apply_missing_strategy(tricky, {"fiber_100g": "median"})

    def test_default_strategy_vocabulary(self):
        assert set(DEFAULT_STRATEGY.values()) <= {"keep", "flag", "drop_column"}


# ============================================================================
# CONTRAT DE SORTIE ET PIPELINE
# ============================================================================

class TestValidateOutput:
    def test_raw_data_rejected(self, tricky):
        typed, _ = type_columns(tricky)
        with pytest.raises(ValueError, match="sugars_100g:max_bound"):
            validate_output(typed)

    def test_duplicate_code_rejected(self):
        typed, _ = type_columns(make_products({}, {}))
        with pytest.raises(ValueError, match="field_uniqueness"):
            validate_output(typed)


class TestClean:
    def test_tricky_products(self, tricky):
        df, reports = clean(tricky)
        assert [report.rule for report in reports] == [
            *(rule.__name__ for rule in ALL_RULES), "validate_output"
        ]
        # écartés : doublon (4), inclassable (7), sans nutriment (8), code interne (9), code à 14 chiffres (10)
        assert sorted(df.index) == [0, 1, 2, 3, 5, 6, 11, 12]

    def test_sample_passes_schema(self, sample):
        df, reports = clean(sample)
        assert schema.find_failures(df, schema.OUTPUT_SCHEMA) == {}
        assert reports[-1].lines_after == len(df)
