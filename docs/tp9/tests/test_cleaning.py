"""
Tests pytest pour le module de nettoyage — TP 9
Couverture : nominal, cas tordus, pureté, idempotence
"""

import pytest
import pandas as pd
import numpy as np
from cleaning import (
    CompteRendu,
    typer_colonnes, normaliser_unites, borner_nutriments,
    corriger_energie, dedupliquer_codes, traiter_categories_vides,
    strategie_manquants, nettoyer
)


# ============================================================================
# FIXTURE : PRODUITS TORDUS (CAS DE TEST)
# ============================================================================

@pytest.fixture
def df_tordu():
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

class TestTyperColonnes:
    def test_nominal(self, df_tordu):
        """Les types sont correctement appliqués."""
        df, rapport = typer_colonnes(df_tordu)
        assert df["code"].dtype == object or df["code"].dtype == "string"
        assert df["energy_100g"].dtype == "float64"
        assert rapport.regle == "typer_colonnes"
        assert rapport.lignes_avant == rapport.lignes_apres  # Pas de perte

    def test_purete(self, df_tordu):
        """L'entrée n'est pas modifiée."""
        df_copie = df_tordu.copy()
        df, _ = typer_colonnes(df_tordu)
        pd.testing.assert_frame_equal(df_tordu, df_copie)


# ============================================================================
# TESTS : NORMALISER UNITÉS
# ============================================================================

class TestNormaliserUnites:
    def test_kcal_depuis_kj(self, df_tordu):
        """kcal dérivée de kJ si absent."""
        df, rapport = normaliser_unites(df_tordu)
        # Row 6 : energy_100g = 1500, kcal manquant → doit être dérivée
        assert df.loc[6, "energy-kcal_100g"] == pytest.approx(1500 / 4.184, rel=0.01)
        assert rapport.details.get("kcal_derivees_kj", 0) > 0

    def test_incohérence_kj_kcal(self, df_tordu):
        """Ratio kJ/kcal hors [3.9, 4.5] → recalcul."""
        df, rapport = normaliser_unites(df_tordu)
        # Row 0 : energy_100g=2000, kcal=74000 → ratio > 4.5
        assert rapport.details.get("kcal_recalculees", 0) > 0

    def test_sodium_depuis_sel(self, df_tordu):
        """sodium dérivé depuis sel si absent."""
        df_test = pd.DataFrame({
            "code": ["001"],
            "salt_100g": [2.5],
            "sodium_100g": [np.nan],
        })
        df, rapport = normaliser_unites(df_test)
        assert df.loc[0, "sodium_100g"] == pytest.approx(1.0, rel=0.01)
        assert rapport.details.get("sodium_derive_sel", 0) == 1


# ============================================================================
# TESTS : BORNER NUTRIMENTS
# ============================================================================

class TestBornerNutriments:
    def test_negatifs_invalides(self, df_tordu):
        """Valeurs négatives → NA."""
        df, rapport = df_tordu.copy(), None
        df, rapport = borner_nutriments(df)
        # Row 5 : fat_100g = -5 → doit devenir NaN
        assert pd.isna(df.loc[5, "fat_100g"])

    def test_over100_invalides(self, df_tordu):
        """Valeurs > 100 g/100g → NA."""
        df, rapport = borner_nutriments(df_tordu)
        # Row 6 : fat_100g = 150 → NaN, sugars_100g = 200 → NaN
        assert pd.isna(df.loc[6, "fat_100g"])
        assert pd.isna(df.loc[6, "sugars_100g"])

    def test_sucres_coherence(self, df_tordu):
        """sugars > glucides + 0.5 → sucres NA."""
        df, rapport = borner_nutriments(df_tordu)
        # Row 5 : sugars=150, carbs=50 → sucres NA
        assert pd.isna(df.loc[5, "sugars_100g"])
        assert rapport.details.get("sucres_incohérents", 0) > 0

    def test_valeur_coherente_conservée(self, df_tordu):
        """Valeur légitime ne change pas."""
        df, rapport = borner_nutriments(df_tordu)
        # Row 3 : fat=82 (normal) → conservé
        assert df.loc[3, "fat_100g"] == 82.0


# ============================================================================
# TESTS : CORRIGER ÉNERGIE
# ============================================================================

class TestCorrigerEnergie:
    def test_kcal_nul_recalcul(self):
        """kcal nul avec macronutriments → recalcul."""
        df = pd.DataFrame({
            "code": ["001"],
            "energy-kcal_100g": [np.nan],
            "proteins_100g": [10.0],
            "carbohydrates_100g": [50.0],
            "fat_100g": [20.0],
        })
        df, rapport = corriger_energie(df)
        # 10*4 + 50*4 + 20*9 = 40 + 200 + 180 = 420 kcal
        assert df.loc[0, "energy-kcal_100g"] == pytest.approx(420, rel=0.01)
        assert rapport.details.get("nulles_recalculees", 0) == 1

    def test_over900_invalidee(self):
        """kcal > 900 → NA ou recalcul."""
        df = pd.DataFrame({
            "code": ["001"],
            "energy-kcal_100g": [1000.0],
            "proteins_100g": [np.nan],
            "carbohydrates_100g": [np.nan],
            "fat_100g": [np.nan],
        })
        df, rapport = corriger_energie(df)
        assert pd.isna(df.loc[0, "energy-kcal_100g"])

    def test_over900_avec_nutrients_recalcul(self):
        """kcal > 900 mais nutriments OK → recalcul."""
        df = pd.DataFrame({
            "code": ["001"],
            "energy-kcal_100g": [1200.0],
            "proteins_100g": [20.0],
            "carbohydrates_100g": [60.0],
            "fat_100g": [15.0],
        })
        df, rapport = corriger_energie(df)
        # 20*4 + 60*4 + 15*9 = 80 + 240 + 135 = 455 kcal
        assert df.loc[0, "energy-kcal_100g"] == pytest.approx(455, rel=0.01)


# ============================================================================
# TESTS : DÉDUPLIQUER
# ============================================================================

class TestDedupliquerCodes:
    def test_exclure_sans_code(self):
        """Lignes sans code → exclues."""
        df = pd.DataFrame({
            "code": ["001", np.nan, "003"],
            "product_name": ["A", "B", "C"],
            "completeness": [0.9, 0.5, 0.8],
            "last_modified_t": [1000, 2000, 3000],
        })
        df, rapport = dedupliquer_codes(df)
        assert len(df) == 2
        assert rapport.details.get("sans_code_exclus", 0) == 1

    def test_doublons_supprimes(self):
        """Doublons → garder le plus complet."""
        df = pd.DataFrame({
            "code": ["001", "001"],
            "product_name": ["A", "A"],
            "completeness": [0.5, 0.9],
            "last_modified_t": [1000, 2000],
        })
        df, rapport = dedupliquer_codes(df)
        assert len(df) == 1
        assert df.loc[0, "completeness"] == 0.9

    def test_purete(self, df_tordu):
        """L'entrée n'est pas modifiée."""
        df_copie = df_tordu.copy()
        df, _ = dedupliquer_codes(df_tordu)
        pd.testing.assert_frame_equal(df_tordu, df_copie)


# ============================================================================
# TESTS : TRAITER CATÉGORIES
# ============================================================================

class TestTraiterCategoriesVides:
    def test_rayon_vide_rempli(self):
        """Rayon vide → "unknown"."""
        df = pd.DataFrame({
            "code": ["001"],
            "main_category": [np.nan],
            "categories_tags": ["snacks"],
        })
        df, rapport = traiter_categories_vides(df)
        assert df.loc[0, "main_category"] == "unknown"

    def test_drapeau_categorie_vide(self):
        """Catégorie vide → drapeau."""
        df = pd.DataFrame({
            "code": ["001"],
            "main_category": ["snacks"],
            "categories_tags": [np.nan],
        })
        df, rapport = traiter_categories_vides(df)
        assert df.loc[0, "categorie_vide"] == 1

    def test_exclure_inclassables(self):
        """Pas de catégories ET rayon unknown → exclus."""
        df = pd.DataFrame({
            "code": ["001", "002"],
            "main_category": ["unknown", "snacks"],
            "categories_tags": [np.nan, "snacks"],
        })
        df, rapport = traiter_categories_vides(df)
        assert len(df) == 1  # "001" exclus
        assert rapport.details.get("inclassables_exclus", 0) == 1


# ============================================================================
# TESTS : IDEMPOTENCE
# ============================================================================

class TestIdempotence:
    def test_idempotence_typage(self, df_tordu):
        """Appliquer deux fois donne le même résultat."""
        df1, r1 = typer_colonnes(df_tordu)
        df2, r2 = typer_colonnes(df1)
        pd.testing.assert_frame_equal(df1, df2)
        assert r2.lignes_touchees == 0

    def test_idempotence_normaliser(self, df_tordu):
        """Appliquer deux fois ne change rien."""
        df1, r1 = normaliser_unites(df_tordu)
        df2, r2 = normaliser_unites(df1)
        pd.testing.assert_frame_equal(df1, df2)

    def test_idempotence_borner(self, df_tordu):
        """Appliquer deux fois ne change rien."""
        df1, r1 = borner_nutriments(df_tordu)
        df2, r2 = borner_nutriments(df1)
        pd.testing.assert_frame_equal(df1, df2)

    def test_idempotence_dedupliquer(self, df_tordu):
        """Appliquer deux fois ne change rien."""
        df1, r1 = dedupliquer_codes(df_tordu)
        df2, r2 = dedupliquer_codes(df1)
        pd.testing.assert_frame_equal(df1, df2)


# ============================================================================
# TESTS : PIPELINE COMPLET
# ============================================================================

class TestPipelineComplet:
    def test_pipeline_structure(self, df_tordu):
        """Le pipeline retourne (DataFrame, liste de rapports)."""
        df, rapports = nettoyer(df_tordu)
        assert isinstance(df, pd.DataFrame)
        assert isinstance(rapports, list)
        assert len(rapports) > 0
        assert all(isinstance(r, CompteRendu) for r in rapports)

    def test_pipeline_qualite(self, df_tordu):
        """Après nettoyage, données plus robustes."""
        df_avant = df_tordu.copy()
        df_apres, _ = nettoyer(df_tordu)

        # Moins de valeurs aberrantes
        assert (df_apres["energy-kcal_100g"] <= 900).all() or df_apres["energy-kcal_100g"].isna().all()

        # Cohérence sucres < glucides
        mask = df_apres["sugars_100g"].notna() & df_apres["carbohydrates_100g"].notna()
        assert (df_apres.loc[mask, "sugars_100g"] <= df_apres.loc[mask, "carbohydrates_100g"] + 0.5).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
