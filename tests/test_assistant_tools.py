"""Registre de plugins et contrat de `chercher_produit` (TP 18), sur un faux catalogue en mémoire."""

import json

import pytest
from fakes import fake_catalog

from nutriscope.catalog import build_fiche, search_words
from nutriscope.tools import ToolContext, ToolRegistry
from nutriscope.tools.search_product import SearchProductTool

SHEET_NUTRIENTS = {"kcal", "lipides", "satures", "sucres", "sel", "fibres", "proteines"}


@pytest.fixture
def registry():
    return ToolRegistry.discover(ToolContext(catalog=fake_catalog()))


def search(registry, arguments):
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
    result = registry.run("chercher_produit", raw)
    json.dumps(result)                       # toujours sérialisable pour le modèle
    return result


# --- plugins -----------------------------------------------------------------

def test_discovery_finds_the_search_plugin(registry):
    assert "chercher_produit" in registry.names
    schema = registry.schemas()[0]["function"]
    assert set(schema["parameters"]["properties"]) == {"nom", "code", "limite"}


def test_a_plugin_without_its_dependency_is_not_loaded():
    assert "chercher_produit" not in ToolRegistry.discover(ToolContext(catalog=None)).names


def test_unknown_tool_is_reported_not_raised(registry):
    assert "erreur" in registry.run("supprimer_base", "{}")
    assert "erreur" in registry.run(None, "{}")


# --- résultats -----------------------------------------------------------------

def test_search_by_code_returns_one_complete_sheet(registry):
    result = search(registry, {"code": "3000000000017"})
    assert result["statut"] == "ok" and result["total"] == 1
    sheet = result["produits"][0]
    assert {"code", "nom", "nutriscore", "nutriments", "donnees_incompletes"} <= set(sheet)
    assert set(sheet["nutriments"]) == SHEET_NUTRIENTS
    assert sheet["nutriscore"] == "E"


def test_code_takes_precedence_over_name(registry):
    result = search(registry, {"code": "3000000000048", "nom": "biscuit"})
    assert result["statut"] == "ok" and result["produits"][0]["nom"] == "Yaourt nature"


def test_name_search_ignores_case_and_accents(registry):
    result = search(registry, {"nom": "PATE A TARTINER"})
    assert result["statut"] == "ok" and result["produits"][0]["code"] == "3000000000017"


def test_name_search_also_matches_the_brand(registry):
    assert search(registry, {"nom": "biscuit marque-b"})["total"] == 2


def test_several_matches_are_ambiguous_and_limited(registry):
    result = search(registry, {"nom": "biscuit", "limite": 1})
    assert result["statut"] == "ambigu" and result["total"] == 2 and len(result["produits"]) == 1


def test_unknown_product(registry):
    assert search(registry, {"nom": "caviar"}) == {"statut": "introuvable", "total": 0, "produits": []}


def test_unknown_value_is_null_never_zero_and_flags_incomplete(registry):
    sheet = search(registry, {"code": "3000000000017"})["produits"][0]
    assert sheet["nutriments"]["fibres"] is None and sheet["donnees_incompletes"] is True


def test_missing_nutriscore_is_null(registry):
    sheet = search(registry, {"code": "3000000000048"})["produits"][0]
    assert sheet["nutriscore"] is None and sheet["donnees_incompletes"] is True
    assert sheet["nutriments"]["fibres"] == 0.0          # un vrai 0 du catalogue reste 0


def test_upc_a_finds_the_ean13_with_leading_zero():
    tool = SearchProductTool(type(fake_catalog())([{"code": "0012345678905", "name": "Test"}]))
    assert tool({"code": "012345678905"})["statut"] == "ok"


# --- arguments invalides : {"erreur": ...}, jamais d'exception -------------------

@pytest.mark.parametrize("arguments", [
    "{not json",                                  # JSON illisible
    "[1, 2]",                                     # pas un objet
    {},                                           # ni nom ni code
    {"nom": "  "},                                # nom vide
    {"nom": "nutella", "rayon": "x"},             # argument inconnu
    {"nom": "nutella", "limite": 0},              # hors bornes
    {"nom": "nutella", "limite": 6},
    {"nom": "nutella", "limite": "3"},            # pas un entier
    {"nom": "nutella", "limite": True},
    {"code": 3017620422003},                      # pas un texte
    {"code": "30176abc"},                         # pas des chiffres
    {"nom": "x" * 500},                           # trop long
    {"nom": "'; DROP TABLE products; --"},        # seuls des mots sont cherchés : pas d'erreur, mais aucun résultat
])
def test_invalid_arguments_return_an_error(registry, arguments):
    result = search(registry, arguments)
    if arguments == {"nom": "'; DROP TABLE products; --"}:
        assert result["statut"] == "introuvable"
    else:
        assert set(result) == {"erreur"} and result["erreur"]


def test_search_words_are_safe_for_like_patterns():
    assert search_words("Prince goût chocolat 100% blé!") == ["prince", "gout", "chocolat", "100", "ble"]


def test_build_fiche_converts_decimals_and_nan():
    from decimal import Decimal

    sheet = build_fiche({"code": 1, "name": "x", "sugars_100g": Decimal("4.50"), "salt_100g": float("nan"),
                         "nutriscore_grade": "not-applicable"})
    assert sheet["nutriments"]["sucres"] == 4.5 and sheet["nutriments"]["sel"] is None
    assert sheet["nutriscore"] is None and sheet["code"] == "1"
