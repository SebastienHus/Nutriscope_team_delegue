"""
Tests pytest du moteur de substitution — TP 16 (après-midi).

Chaque règle de `suggest()` est vérifiée isolément sur un petit catalogue synthétique :
gardes (code inconnu, données incohérentes, alcool, Nutri-Score manquant), même
sous-catégorie et même rayon, Nutri-Score strictement meilleur, rayon de distance,
doublons, labels (contraintes alimentaires strictes, labels de qualité prioritaires),
ordre de tri et format de sortie attendu par l'API.
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.exceptions import NotFittedError

from nutriscope.clustering import FIBER
from nutriscope.substitution import (
    OUTPUT_COLUMNS,
    NotSubstitutableError,
    ProductNotFoundError,
    SubstitutionEngine,
    identity_key,
    label_flags,
)

BISCUIT = {"energy-kcal_100g": 480.0, "fat_100g": 20.0, "saturated-fat_100g": 10.0,
           "carbohydrates_100g": 65.0, "sugars_100g": 30.0, "proteins_100g": 6.0,
           "salt_100g": 0.5, FIBER: 3.0}
JUICE = {"energy-kcal_100g": 45.0, "fat_100g": 0.0, "saturated-fat_100g": 0.0,
         "carbohydrates_100g": 10.0, "sugars_100g": 9.0, "proteins_100g": 0.5,
         "salt_100g": 0.01, FIBER: 0.2}


def row(code, grade, name=None, brand="brand", aisle="Sugary snacks", group="Biscuits and cakes",
        labels=None, **nutrients):
    return {"code": code, "product_name": name or f"product {code}", "brands": brand,
            "nutriscore_grade": grade, "pnns_groups_1": aisle, "pnns_groups_2": group,
            "labels_tags": labels, **{**BISCUIT, **nutrients}}


@pytest.fixture
def catalog() -> pd.DataFrame:
    rows = [
        row("target", "e"),                                         # produit scanné
        row("same_e", "e", sugars_100g=29.0),                       # pas mieux noté
        row("close_d", "d", sugars_100g=28.0),                      # mieux noté, très proche
        row("close_c", "c", sugars_100g=25.0),                      # mieux noté, proche
        row("far_a", "a", **{"fat_100g": 1.0, "saturated-fat_100g": 0.2, "sugars_100g": 1.0,
                             "proteins_100g": 30.0, FIBER: 20.0}),  # mieux noté mais trop loin
        row("other_group", "a", group="Chocolate products"),        # autre sous-catégorie
        row("dup_1", "c", name="Twin cookie", brand="Acme", sugars_100g=26.0),
        row("dup_2", "c", name="TWIN  Cookie!", brand="acme", sugars_100g=26.5),  # même produit
        row("bad_salt", "b", aisle="Beverages", group="Fruit juices", **{**JUICE, "salt_100g": 20.0}),
        row("beer", "c", aisle="Alcoholic beverages", group="Alcoholic beverages", **JUICE),
        row("no_grade", None),
        row("best", "a", sugars_100g=22.0),                        # le mieux noté, proche
    ]
    # Des jus pour donner au catalogue une dispersion réaliste
    rows += [row(f"juice_{i}", "c", aisle="Beverages", group="Fruit juices",
                 **{**JUICE, "sugars_100g": 8.0 + i / 10}) for i in range(10)]
    return pd.DataFrame(rows)


@pytest.fixture
def engine(catalog) -> SubstitutionEngine:
    return SubstitutionEngine(max_distance=1.5).fit(catalog)


def codes(result: pd.DataFrame) -> list[str]:
    return result["code"].tolist()


# ============================================================================
# GARDES
# ============================================================================

def test_unknown_code_raises_not_found(engine):
    with pytest.raises(ProductNotFoundError):
        engine.suggest("does-not-exist")


@pytest.mark.parametrize("code", ["bad_salt", "beer", "no_grade"])
def test_non_substitutable_products(engine, code):
    with pytest.raises(NotSubstitutableError):
        engine.suggest(code)


def test_implausible_products_are_never_suggested(engine, catalog):
    assert "bad_salt" not in engine.catalog_["code"].tolist()
    assert "bad_salt" in engine.rejected_codes_


def test_suggest_requires_fit():
    with pytest.raises(NotFittedError):
        SubstitutionEngine().suggest("target")


def test_fit_rejects_missing_columns(catalog):
    with pytest.raises(ValueError, match="Missing columns"):
        SubstitutionEngine().fit(catalog.drop(columns="pnns_groups_2"))


def test_fit_rejects_duplicated_codes(catalog):
    with pytest.raises(ValueError, match="Duplicated"):
        SubstitutionEngine().fit(pd.concat([catalog, catalog.head(1)]))


def test_invalid_n(engine):
    with pytest.raises(ValueError):
        engine.suggest("target", n=0)


# ============================================================================
# FILTRES
# ============================================================================

def test_only_same_subcategory_and_strictly_better(engine):
    result = engine.suggest("target", n=20)
    assert "other_group" not in codes(result)
    assert "same_e" not in codes(result)
    assert "target" not in codes(result)
    assert set(result["nutriscore_grade"]) <= {"a", "b", "c", "d"}
    assert all(code.startswith(("close", "dup", "best")) for code in codes(result))


def test_distance_radius(catalog):
    assert "far_a" not in codes(SubstitutionEngine(max_distance=1.5).fit(catalog).suggest("target", n=20))
    assert "far_a" in codes(SubstitutionEngine(max_distance=100.0).fit(catalog).suggest("target", n=20))


def test_best_product_has_no_suggestion(engine):
    result = engine.suggest("best")
    assert result.empty
    assert list(result.columns) == list(OUTPUT_COLUMNS)


def test_duplicates_are_collapsed(engine):
    result = engine.suggest("target", n=20)
    assert len({"dup_1", "dup_2"} & set(codes(result))) == 1


def test_same_product_under_another_code_is_excluded(catalog):
    catalog = pd.concat([catalog, pd.DataFrame([row("target_bis", "d", name="product target")])])
    result = SubstitutionEngine().fit(catalog).suggest("target", n=20)
    assert "target_bis" not in codes(result)


# ============================================================================
# CLASSEMENT ET SORTIE
# ============================================================================

def test_sorted_by_grade_then_distance(engine):
    result = engine.suggest("target", n=20)
    keys = list(zip(result["nutriscore_grade"], result["distance"]))
    assert keys == sorted(keys)
    assert result["rank"].tolist() == list(range(1, len(result) + 1))


def test_n_limits_the_output(engine):
    assert len(engine.suggest("target", n=2)) == 2


def test_output_format(engine):
    result = engine.suggest("target")
    assert list(result.columns) == list(OUTPUT_COLUMNS)
    assert (result["distance"] >= 0).all()


def set_labels(catalog, code, labels):
    catalog.loc[catalog["code"] == code, "labels_tags"] = labels


def test_quality_label_gives_priority(catalog):
    set_labels(catalog, "target", "en:organic,fr:ab-agriculture-biologique")
    set_labels(catalog, "close_d", "en:organic")
    result = SubstitutionEngine().fit(catalog).suggest("target", n=20)
    assert codes(result)[0] == "close_d"           # bio D passe avant les C et A non bio
    assert result["shared_labels"].iloc[0] == 1
    assert "organic" in result["labels"].iloc[0]
    assert len(result) > 1, "a quality label is a preference, not a filter"


def test_more_shared_quality_labels_rank_first(catalog):
    set_labels(catalog, "target", "en:organic,en:fair-trade")
    set_labels(catalog, "close_d", "en:organic")
    set_labels(catalog, "close_c", "en:organic,en:fairtrade-international")
    result = SubstitutionEngine().fit(catalog).suggest("target", n=20)
    assert codes(result)[:2] == ["close_c", "close_d"]
    assert result["shared_labels"].tolist()[:2] == [2, 1]


def test_quality_labels_ignored_for_unlabelled_product(catalog):
    set_labels(catalog, "close_d", "en:organic")
    result = SubstitutionEngine().fit(catalog).suggest("target", n=20)
    assert codes(result)[0] == "best"              # le mieux noté d'abord
    assert (result["shared_labels"] == 0).all()


def test_dietary_label_is_a_strict_filter(catalog):
    set_labels(catalog, "target", "en:no-gluten")
    set_labels(catalog, "close_c", "en:no-gluten,en:organic")
    result = SubstitutionEngine().fit(catalog).suggest("target", n=20)
    assert codes(result) == ["close_c"]


def test_dietary_constraint_without_compatible_candidate_gives_empty(catalog):
    set_labels(catalog, "target", "en:halal")
    assert SubstitutionEngine().fit(catalog).suggest("target").empty


def test_vegan_satisfies_vegetarian(catalog):
    set_labels(catalog, "target", "en:vegetarian")
    set_labels(catalog, "close_d", "en:vegan")
    set_labels(catalog, "close_c", "en:european-vegetarian-union")
    result = SubstitutionEngine().fit(catalog).suggest("target", n=20)
    assert set(codes(result)) == {"close_d", "close_c"}


def test_vegetarian_does_not_satisfy_vegan(catalog):
    set_labels(catalog, "target", "en:vegan")
    set_labels(catalog, "close_d", "en:vegetarian")
    assert SubstitutionEngine().fit(catalog).suggest("target").empty


def test_irrelevant_tags_are_ignored(catalog):
    set_labels(catalog, "target", "en:green-dot,en:made-in-france,en:nutriscore-grade-e")
    result = SubstitutionEngine().fit(catalog).suggest("target", n=20)
    assert codes(result)[0] == "best"
    assert (result["labels"] == "").all()


def test_works_without_labels_column(catalog):
    engine = SubstitutionEngine().fit(catalog.drop(columns="labels_tags"))
    assert not engine.labels_available_
    result = engine.suggest("target", n=20)
    assert codes(result)[0] == "best"
    assert (result["shared_labels"] == 0).all()


# ============================================================================
# OUTILS
# ============================================================================

def test_label_flags_map_tags_to_labels():
    flags = label_flags(pd.Series(["en:eu-organic, en:vegan", "en:organic-x", None, "fr:label-rouge"]))
    assert flags.loc[0, "organic"] and flags.loc[0, "vegan"]
    assert not flags.loc[1].any()                  # tag inconnu : pas de correspondance partielle
    assert not flags.loc[2].any()
    assert flags.loc[3, "label_rouge"]


def test_identity_key_normalizes_and_ignores_missing_names():
    keys = identity_key(pd.Series(["Crème  brûlée!", "creme brulee", None]),
                        pd.Series(["Acme", "ACME", "Acme"]))
    assert keys[0] == keys[1] != ""
    assert keys[2] == ""
    assert np.all(keys.map(type) == str)


def test_identity_key_requires_a_brand():
    # Sans marque, un nom générique désigne des produits différents : jamais doublons
    keys = identity_key(pd.Series(["Pain complet", "Pain complet"]), pd.Series([None, ""]))
    assert (keys == "").all()


def test_generic_unbranded_products_are_not_merged(catalog):
    extra = pd.DataFrame([row("bread_c", "c", name="Pain complet", brand=None, group="Bread"),
                          row("bread_a", "a", name="Pain complet", brand=None, group="Bread",
                              sugars_100g=26.0)])
    result = SubstitutionEngine().fit(pd.concat([catalog, extra])).suggest("bread_c")
    assert codes(result) == ["bread_a"]
