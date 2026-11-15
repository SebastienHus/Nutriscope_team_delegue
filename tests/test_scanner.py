"""Workflow du scanner avec un FAUX client de vision : forme du contrat, contrôles, vote, aiguillage, relecture."""

import io
import json

import pytest
from fakes import FAKE_CONFIG, FakeChatClient, fake_catalog, text_reply

from nutriscope.scanner import LabelScanner, answer_question
from nutriscope.scanner.answer import fallback_answer, review
from nutriscope.scanner.ean import check_digit, is_valid_barcode
from nutriscope.scanner.validation import Reading, check_reading, extract_json, parse_printed, to_reading
from nutriscope.scanner.vote import vote
from nutriscope.tools import ToolContext, ToolRegistry

NUTRIENTS = ("kj", "kcal", "lipides", "satures", "glucides", "sucres", "fibres", "proteines", "sel")


@pytest.fixture
def png_bytes():
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def label_json(**changes):
    data = {"tableau_visible": True, "nom": "Pâte à tartiner noisette", "marque": "Marque A",
            "code_barres": "3000000000017", "base": "pour 100 g",
            "nutriments": {"kj": "2252 kJ", "kcal": "539 kcal", "lipides": "30,9 g", "satures": "10,6 g",
                           "glucides": "57,5 g", "sucres": "56,3 g", "fibres": None, "proteines": "6,3 g",
                           "sel": "0,107 g"},
            "ingredients": "sucre, huile de palme, noisettes 13%"}
    data.update(changes)
    return json.dumps(data, ensure_ascii=False)


def make_scanner(replies, **kwargs):
    registry = ToolRegistry.discover(ToolContext(catalog=fake_catalog()))
    return LabelScanner(registry=registry, client=FakeChatClient(replies), config=FAKE_CONFIG, **kwargs)


# --- EAN ----------------------------------------------------------------------

def test_ean13_check_digit_examples_of_the_brief():
    assert is_valid_barcode("3154230810131")
    assert not is_valid_barcode("3154230810137")
    assert is_valid_barcode("3017620422003") and check_digit("301762042200") == 3
    assert is_valid_barcode("96385074")          # EAN-8


# --- lecture des valeurs et contrôles ---------------------------------------------

@pytest.mark.parametrize("text, key, expected", [
    ("1,1 g", "sel", (1.1, False)),
    ("< 0,5 g", "sucres", (0.5, True)),
    ("moins de 0.5g", "sucres", (0.5, True)),
    ("2255 kJ / 539 kcal", "kcal", (539.0, False)),
    ("2255 kJ / 539 kcal", "kj", (2255.0, False)),
    ("539 kcal", "kj", (None, False)),
    ("traces", "sel", (None, False)),
    (None, "fibres", (None, False)),
    (0, "fibres", (None, False)),               # 0 nu : valeur inventée typique
    (3.8, "fibres", (3.8, False)),
])
def test_parse_printed(text, key, expected):
    assert parse_printed(text, key) == expected


def test_extract_json_ignores_text_around():
    assert extract_json('Voici :\n```json\n{"nom": "x"}\n```') == {"nom": "x"}
    assert extract_json("pas de json") is None


def test_checks_catch_inconsistent_labels():
    reading = Reading(base="100 g")
    reading.nutriments.update(kj=2252.0, kcal=339.0, lipides=10.0, satures=12.0, glucides=5.0, sucres=50.0)
    messages = " | ".join(message for message, _ in check_reading(reading))
    assert "kJ" in messages and "saturés" in messages and "sucres" in messages


def test_no_table_means_no_values():
    reading, _ = to_reading(json.loads(label_json(tableau_visible=False)))
    assert not reading.has_values and reading.alerts


# --- vote ---------------------------------------------------------------------

def test_vote_field_by_field():
    readings = []
    for salt, fibre in ((1.1, 3.8), (1.10, None), (11.0, 3.0)):
        reading = Reading()
        reading.nutriments.update(sel=salt, fibres=fibre)
        readings.append(reading)
    result = vote(readings)
    assert result.nutriments["sel"] == 1.1
    assert result.nutriments["fibres"] is None and any("fibres" in alert for alert in result.alerts)


# --- workflow complet -------------------------------------------------------------

def check_contract(result):
    assert set(result) >= {"statut", "produit", "base", "nutriments", "inferieur_a", "ingredients",
                           "fiche_catalogue", "ecarts", "alertes", "mesures"}
    assert set(result["nutriments"]) == set(NUTRIENTS)
    json.dumps(result)


def test_fake_image_is_unreadable_without_model_call():
    scanner = make_scanner([])
    result = scanner(b"ceci n'est pas une image")
    check_contract(result)
    assert result["statut"] == "illisible" and result["alertes"] and result["mesures"]["appels_modele"] == 0


def test_verified_label_lists_differences(png_bytes):
    scanner = make_scanner([text_reply(label_json(nutriments={
        "kj": "2252 kJ", "kcal": "539 kcal", "lipides": "30,9 g", "satures": "10,6 g", "glucides": "57,5 g",
        "sucres": "50 g", "fibres": None, "proteines": "6,3 g", "sel": "0,107 g"}))])
    result = scanner(png_bytes)
    check_contract(result)
    assert result["statut"] == "verifie" and result["fiche_catalogue"]["code"] == "3000000000017"
    assert result["ecarts"] == [{"champ": "sucres", "etiquette": 50.0, "catalogue": 56.3}]
    assert result["nutriments"]["fibres"] is None


def test_misread_barcode_is_not_used(png_bytes):
    scanner = make_scanner([text_reply(label_json(code_barres="3000000000018", nom="Inconnu", marque=None))])
    result = scanner(png_bytes)
    assert result["statut"] == "non_verifie" and result["fiche_catalogue"] is None and result["ecarts"] == []
    assert any("clé de contrôle" in alert for alert in result["alertes"])


def test_ambiguous_name_stays_unverified(png_bytes):
    scanner = make_scanner([text_reply(label_json(code_barres=None, nom="Biscuit fourré", marque=None))])
    result = scanner(png_bytes)
    assert result["statut"] == "non_verifie" and any("ambigu" in alert for alert in result["alertes"])


def test_invalid_reading_is_retried_then_fields_discarded(png_bytes):
    bad = label_json(nutriments={"kj": "2252 kJ", "kcal": "100 kcal"})
    scanner = make_scanner([text_reply(bad), text_reply(bad)], max_retries=1)
    result = scanner(png_bytes)
    assert result["mesures"]["appels_modele"] == 2
    assert result["nutriments"]["kj"] is None and result["nutriments"]["kcal"] is None


def test_model_unreachable_still_follows_the_contract(png_bytes):
    result = make_scanner([ConnectionError("down")])(png_bytes)
    check_contract(result)
    assert result["statut"] == "illisible" and any("indisponible" in alert for alert in result["alertes"])


def test_three_readings_vote(png_bytes):
    replies = [text_reply(label_json(nutriments={"sel": s, "kcal": "539 kcal"})) for s in ("1,1 g", "1,1 g", "11 g")]
    result = make_scanner(replies, reads=3)(png_bytes)
    assert result["nutriments"]["sel"] == 1.1 and result["mesures"]["appels_modele"] == 3


# --- rédacteur et relecteur -------------------------------------------------------

SCAN = {"statut": "non_verifie", "produit": {"nom": "Soda"}, "base": "100 ml",
        "nutriments": dict.fromkeys(NUTRIENTS) | {"sucres": 10.6}, "inferieur_a": [], "fiche_catalogue": None}


def test_reviewer_rejects_invented_number_and_missing_unverified_mention():
    assert len(review("Il contient 35 g de sucres.", SCAN)) == 2
    assert review("Oui : 10,6 g de sucres pour 100 ml (lecture non vérifiée).", SCAN) == []


def test_writer_review_loop_is_bounded_with_fallback():
    client = FakeChatClient([text_reply("35 g de sucres !"), text_reply("Toujours 35 g.")])
    result = answer_question("C'est sucré ?", SCAN, client, FAKE_CONFIG, max_rounds=2)
    assert not result.accepted and result.rounds == 2
    assert "10,6" in result.text and "non vérifiée" in result.text
    assert review(fallback_answer(SCAN), SCAN) == []


def test_front_photo_is_sent_in_the_same_reading(png_bytes):
    client = FakeChatClient([text_reply(label_json())])
    registry = ToolRegistry.discover(ToolContext(catalog=fake_catalog()))
    scanner = LabelScanner(registry=registry, client=client, config=FAKE_CONFIG)
    result = scanner(png_bytes, face=png_bytes)
    images = [part for part in client.requests[0]["messages"][0]["content"] if part["type"] == "image_url"]
    assert len(images) == 2 and result["statut"] == "verifie"


def test_missing_model_is_named_in_the_alert(png_bytes):
    class NotFoundError(Exception):
        body = {"message": "model 'qwen3-vl:8b-instruct' not found"}

    result = make_scanner([NotFoundError("404")])(png_bytes)
    assert any("not found" in alert for alert in result["alertes"])
