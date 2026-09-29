"""
Tests pytest pour le module de nettoyage — TP 9
Couverture : nominal, cas tordus, pureté, idempotence
"""

import pytest
import pandas as pd
import numpy as np
from cleaning import (
    Report,
    type_columns, normalize_units, limit_nutrients,
    revise_energy, unduplicate_codes, handle_empty_categories,
    clean
)


# ============================================================================
# FIXTURE : PRODUITS TORDUS (CAS DE TEST)
# ============================================================================

@pytest.fixture
def df_extreme():
    """Échantillon de produits avec anomalies du TP 2."""
    return pd.DataFrame({
        "code": ["001", "002", "003", "004", "005", "006", "007", "008"],
        "product_name": ["Sucre", "Sel", "Soda", "Beurre", "Huile", "Test6", "Test7", "Test8"],
        "brands": ["Brand1", "Brand2", None, "Brand4", "Brand5", "Brand6", "Brand7", "Brand8"],
        "main_category": ["sweets", "condiments", "beverages", "dairy", "oils", "unknown", "unknown", "unknown"],
        "categories_tags": ["sweets", "condiments", "beverages", "dairy", "oils", None, "", "snacks"],
        "energy_100g": [2000.0, 0.0, 306.0, 3200.0, 3700.0, 1500.0, np.nan, 100.0],  # 74000 g sucre en théorie
        "energy-kcal_100g": [74000.0, 0.0, 73.0, 800.0, 900.0, 400.0, 50.0, 25.0],  # Énergies aberrantes
        "fat_100g": [0.0, 0.0, 0.0, 82.0, 100.0, -5.0, 150.0, 10.0],  # Négatif et > 100
        "saturated-fat_100g": [0.0, 0.0, 0.0, 50.0, 30.0, 0.0, 100.0, 2.0],
        "carbohydrates_100g": [100.0, 0.0, 11.0, 0.5, 0.0, 50.0, 80.0, 5.0],
        "sugars_100g": [100.0, 0.0, 11.0, 5.0, 0.0, 150.0, 200.0, 1.0],  # 74000 g sucre, > glucides
        "fiber_100g": [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
        "proteins_100g": [0.0, 60.0, 0.0, 0.7, 0.0, 15.0, 5.0, 2.0],
        "salt_100g": [0.0, 5000.0, 0.025, 1.5, 0.0, 0.5, 1.0, 0.1],  # 5000 g sel aberrant
        "sodium_100g": [0.0, 2000.0, 0.01, 0.6, 0.0, 0.2, 0.4, 0.04],
        "nutriscore_grade": ["e", "e", "d", "d", "a", "e", "f", "a"],
        "completeness": [0.9, 0.5, 0.8, 0.95, 1.0, 0.3, 0.2, 0.7],
        "last_modified_t": [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000],
    })


# ============================================================================
# TESTS : TYPAGE
# ============================================================================

class TestTypeColumns:
    def nominal_test(self, df_extreme):
        """Les types sont correctement appliqués."""
        df, report = type_columns(df_extreme)
        assert df["code"].dtype == object or df["code"].dtype == "string"
        assert df["energy_100g"].dtype == "float64"
        assert report.rule == "typer_colonnes"
        assert report.lines_before == report.lines_after  # Pas de perte

    def purity_test(self, df_extreme):
        """L'entrée n'est pas modifiée."""
        df_copy = df_extreme.copy()
        type_columns(df_extreme)
        pd.testing.assert_frame_equal(df_extreme, df_copy)


# ============================================================================
# TESTS : NORMALISER UNITÉS
# ============================================================================

class TestNormalizeUnits:
    def test_kcal_from_kj(self, df_extreme):
        """kcal dérivée de kJ si absent."""
        df, report = normalize_units(df_extreme)
        # Row 6 : energy_100g = 1500, kcal manquant → doit être dérivée
        assert df.loc[6, "energy-kcal_100g"] == pytest.approx(1500 / 4.184, rel=0.01)
        assert report.details.get("kcal_derivees_kj", 0) > 0

    def test_incoherence_kj_kcal(self, df_extreme):
        """Ratio kJ/kcal hors [3.9, 4.5] → recalcul."""
        df, report = normalize_units(df_extreme)
        # Row 0 : energy_100g=2000, kcal=74000 → ratio > 4.5
        assert report.details.get("kcal_recalculees", 0) > 0

    def test_sodium_from_salt(self, df_extreme):
        """sodium dérivé depuis sel si absent."""
        df_test = pd.DataFrame({
            "code": ["001"],
            "salt_100g": [2.5],
            "sodium_100g": [np.nan],
        })
        df, report = normalize_units(df_test)
        assert df.loc[0, "sodium_100g"] == pytest.approx(1.0, rel=0.01)
        assert report.details.get("sodium_derive_sel", 0) == 1


# ============================================================================
# TESTS : BORNER NUTRIMENTS
# ============================================================================

class TestLimitNutrients:
    def test_invalidate_negatives(self, df_extreme):
        """Valeurs négatives → NA."""
        df, report = df_extreme.copy(), None
        df, report = limit_nutrients(df)
        # Row 5 : fat_100g = -5 → doit devenir NaN
        assert pd.isna(df.loc[5, "fat_100g"])

    def test_invalidate_over100(self, df_extreme):
        """Valeurs > 100 g/100g → NA."""
        df, report = limit_nutrients(df_extreme)
        # Row 6 : fat_100g = 150 → NaN, sugars_100g = 200 → NaN
        assert pd.isna(df.loc[6, "fat_100g"])
        assert pd.isna(df.loc[6, "sugars_100g"])

    def test_sugars_coherence(self, df_extreme):
        """sugars > glucides + 0.5 → sucres NA."""
        df, report = limit_nutrients(df_extreme)
        # Row 5 : sugars=150, carbs=50 → sucres NA
        assert pd.isna(df.loc[5, "sugars_100g"])
        assert report.details.get("sucres_incohérents", 0) > 0

    def test_conserve_coherent_value(self, df_extreme):
        """Valeur légitime ne change pas."""
        df, report = limit_nutrients(df_extreme)
        # Row 3 : fat=82 (normal) → conservé
        assert df.loc[3, "fat_100g"] == 82.0


# ============================================================================
# TESTS : CORRIGER ÉNERGIE
# ============================================================================

class TestReviserEnergy:
    def test_kcal_null_recalculate(self):
        """kcal nul avec macronutriments → recalcul."""
        df = pd.DataFrame({
            "code": ["001"],
            "energy-kcal_100g": [np.nan],
            "proteins_100g": [10.0],
            "carbohydrates_100g": [50.0],
            "fat_100g": [20.0],
        })
        df, report = revise_energy(df)
        # 10*4 + 50*4 + 20*9 = 40 + 200 + 180 = 420 kcal
        assert df.loc[0, "energy-kcal_100g"] == pytest.approx(420, rel=0.01)
        assert report.details.get("nulles_recalculees", 0) == 1

    def test_invalidate_over900(self):
        """kcal > 900 → NA ou recalcul."""
        df = pd.DataFrame({
            "code": ["001"],
            "energy-kcal_100g": [1000.0],
            "proteins_100g": [np.nan],
            "carbohydrates_100g": [np.nan],
            "fat_100g": [np.nan],
        })
        df, report = revise_energy(df)
        assert pd.isna(df.loc[0, "energy-kcal_100g"])

    def test_over900_with_nutrients_recalculate(self):
        """kcal > 900 mais nutriments OK → recalcul."""
        df = pd.DataFrame({
            "code": ["001"],
            "energy-kcal_100g": [1200.0],
            "proteins_100g": [20.0],
            "carbohydrates_100g": [60.0],
            "fat_100g": [15.0],
        })
        df, report = revise_energy(df)
        # 20*4 + 60*4 + 15*9 = 80 + 240 + 135 = 455 kcal
        assert df.loc[0, "energy-kcal_100g"] == pytest.approx(455, rel=0.01)


# ============================================================================
# TESTS : DÉDUPLIQUER
# ============================================================================

class TestUnduplicateCodes:
    def test_exclude_without_code(self):
        """Lignes sans code → exclues."""
        df = pd.DataFrame({
            "code": ["001", np.nan, "003"],
            "product_name": ["A", "B", "C"],
            "completeness": [0.9, 0.5, 0.8],
            "last_modified_t": [1000, 2000, 3000],
        })
        df, report = unduplicate_codes(df)
        assert len(df) == 2
        assert report.details.get("sans_code_exclus", 0) == 1

    def test_duplicates_drop(self):
        """Doublons → garder le plus complet."""
        df = pd.DataFrame({
            "code": ["001", "001"],
            "product_name": ["A", "A"],
            "completeness": [0.5, 0.9],
            "last_modified_t": [1000, 2000],
        })
        df, report = unduplicate_codes(df)
        assert len(df) == 1
        assert df.loc[0, "completeness"] == 0.9

    def test_purity(self, df_extreme):
        """L'entrée n'est pas modifiée."""
        df_copy = df_extreme.copy()
        unduplicate_codes(df_extreme)
        pd.testing.assert_frame_equal(df_extreme, df_copy)


# ============================================================================
# TESTS : TRAITER CATÉGORIES
# ============================================================================

class TestHandlerEmptyCategories:
    def test_empty_group_filled(self):
        """Rayon vide → "unknown"."""
        df = pd.DataFrame({
            "code": ["001"],
            "main_category": [np.nan],
            "categories_tags": ["snacks"],
        })
        df, report = handle_empty_categories(df)
        assert df.loc[0, "main_category"] == "unknown"

    def test_flag_empty_category(self):
        """Catégorie vide → drapeau."""
        df = pd.DataFrame({
            "code": ["001"],
            "main_category": ["snacks"],
            "categories_tags": [np.nan],
        })
        df, report = handle_empty_categories(df)
        assert df.loc[0, "categorie_vide"] == 1

    def test_exclude_unclassable(self):
        """Pas de catégories ET rayon unknown → exclus."""
        df = pd.DataFrame({
            "code": ["001", "002"],
            "main_category": ["unknown", "snacks"],
            "categories_tags": [np.nan, "snacks"],
        })
        df, report = handle_empty_categories(df)
        assert len(df) == 1  # "001" exclus
        assert report.details.get("inclassables_exclus", 0) == 1


# ============================================================================
# TESTS : IDEMPOTENCE
# ============================================================================

class TestIdempotence:
    def test_typing_idempotence(self, df_extreme):
        """Appliquer deux fois donne le même résultat."""
        df1, r1 = type_columns(df_extreme)
        df2, r2 = type_columns(df1)
        pd.testing.assert_frame_equal(df1, df2)
        assert r2.lines_changed == 0

    def test_normalize_idempotence(self, df_extreme):
        """Appliquer deux fois ne change rien."""
        df1, r1 = normalize_units(df_extreme)
        df2, r2 = normalize_units(df1)
        pd.testing.assert_frame_equal(df1, df2)

    def test_limit_idempotence(self, df_extreme):
        """Appliquer deux fois ne change rien."""
        df1, r1 = limit_nutrients(df_extreme)
        df2, r2 = limit_nutrients(df1)
        pd.testing.assert_frame_equal(df1, df2)

    def test_unduplicate_idempotence(self, df_extreme):
        """Appliquer deux fois ne change rien."""
        df1, r1 = unduplicate_codes(df_extreme)
        df2, r2 = unduplicate_codes(df1)
        pd.testing.assert_frame_equal(df1, df2)


# ============================================================================
# TESTS : PIPELINE COMPLET
# ============================================================================

class TestCleaningPipeline:
    def test_pipeline_structure(self, df_extreme):
        """Le pipeline retourne (DataFrame, liste de rapports)."""
        df, reports = clean(df_extreme)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(reports, list)
        assert len(reports) > 0
        assert all(isinstance(r, Report) for r in reports)

    def test_pipeline_quality(self, df_extreme):
        """Après nettoyage, données plus robustes."""
        df_before = df_extreme.copy()
        df_after, _ = clean(df_extreme)

        # Moins de valeurs aberrantes
        assert (df_after["energy-kcal_100g"] <= 900).all() or df_after["energy-kcal_100g"].isna().all()

        # Cohérence sucres < glucides
        mask = df_after["sugars_100g"].notna() & df_after["carbohydrates_100g"].notna()
        assert (df_after.loc[mask, "sugars_100g"] <= df_after.loc[mask, "carbohydrates_100g"] + 0.5).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
