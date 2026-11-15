"""Tests du contrat de scan_label (README, « Le seul contrat imposé »).

Ces tests vérifient la **forme** du résultat, pas la qualité de la lecture : celle-ci se
mesure avec ``tools/measure_scanner.py``. Ils appellent seulement ``scan_label`` :
l'organisation de votre code vous appartient.

Photos utilisées (5 lectures par le modèle, plus une fausse image) :

- 02 Prince : un tableau ordinaire, envoyé une fois en chemin, une fois en octets ;
- 01 Nutella : pas de ligne « fibres » sur l'étiquette ;
- 03 Skyr : des valeurs « < 0,5 g » ;
- 08 Alpro : une boisson, valeurs pour 100 ml ;
- 21 Madeleines : la « photo du tableau » ne montre aucun tableau.
"""

from __future__ import annotations

import pytest

from scan_tools.scan_common import RULES, load_ground_truth, photo, rule_dictionary

PRODUCTS = {p["id"]: p for p in load_ground_truth()}
PHOTOS = ("02", "01", "03", "08", "21")


def result_for(scan_once, key: str) -> dict:
    """``key`` = numéro de photo (envoyée en chemin), ``02-bytes`` ou ``fake-image``."""
    if key == "fake-image":
        image = b"ceci n'est pas une image"
    elif key.endswith("-bytes"):
        image = photo(PRODUCTS[key.split("-")[0]]).read_bytes()
    else:
        image = str(photo(PRODUCTS[key]))
    r = scan_once(key, image)
    problems = rule_dictionary(r)
    if problems:
        pytest.fail("résultat incomplet : " + " ; ".join(problems), pytrace=False)
    return r


IMAGES = (*PHOTOS, "02-bytes", "fake-image")


@pytest.mark.parametrize("image", IMAGES)
def test_returns_complete_dict_without_exception(scan_once, image):
    result_for(scan_once, image)


@pytest.mark.parametrize("rule", RULES)
@pytest.mark.parametrize("image", IMAGES)
def test_contract_rule(scan_once, image, rule):
    r = result_for(scan_once, image)
    problems = RULES[rule](r)
    assert not problems, " ; ".join(problems)


def test_fake_image_is_unreadable_with_alert(scan_once):
    r = result_for(scan_once, "fake-image")
    assert r["statut"] == "illisible", f"statut = {r['statut']!r} pour une image qui n'en est pas une"
    assert all(v is None for v in r["nutriments"].values()), "aucune valeur ne peut être lue sur une fausse image"
    assert r["alertes"], "le résultat doit dire en clair ce qui a cloché (alertes vide)"


def test_missing_is_null_never_zero_nutella_fibre(scan_once):
    r = result_for(scan_once, "01")
    assert r["nutriments"]["fibres"] is None, (
        f"fibres = {r['nutriments']['fibres']!r} : l'étiquette du Nutella n'a pas de ligne fibres, il faut null")


def test_photo_without_table_no_values_madeleines(scan_once):
    r = result_for(scan_once, "21")
    read = {k: v for k, v in r["nutriments"].items() if v is not None}
    assert not read, f"la photo 21 ne montre aucun tableau, mais le scanner rend : {read}"


def test_path_and_bytes_give_same_shape(scan_once):
    from_path, from_bytes = result_for(scan_once, "02"), result_for(scan_once, "02-bytes")
    assert set(from_bytes) >= set(from_path) - {"mesures"}, "les octets de l'image doivent donner un résultat aussi complet"
    assert from_bytes["statut"] != "illisible" or from_path["statut"] == "illisible", (
        "la photo 02 est lue depuis son chemin mais pas depuis ses octets")
