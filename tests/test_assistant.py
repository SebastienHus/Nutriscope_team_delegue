"""Boucle de l'assistant et garde-fous, avec un FAUX client de modèle (aucun vrai modèle)."""

import pytest
from fakes import FAKE_BEHAVIOR, FAKE_CONFIG, FakeChatClient, fake_catalog, text_reply, tool_reply

from nutriscope.assistant import Assistant, load_behavior
from nutriscope.assistant.config import load_config, ollama_host
from nutriscope.assistant.guards import medical_refusal, unsupported_numbers
from nutriscope.tools import ToolContext, ToolRegistry


def make_assistant(replies, **kwargs):
    client = FakeChatClient(replies)
    registry = ToolRegistry.discover(ToolContext(catalog=fake_catalog()))
    return Assistant(registry, client=client, config=FAKE_CONFIG, behavior=FAKE_BEHAVIOR, **kwargs), client


# --- configuration -------------------------------------------------------------

@pytest.mark.parametrize("value, expected", [
    (None, "http://localhost:11434"),
    ("0.0.0.0:11434", "http://localhost:11434"),
    ("http://llm:11434/", "http://llm:11434"),
    ("https://ollama.example.org", "https://ollama.example.org"),
])
def test_ollama_host_from_environment(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("OLLAMA_HOST", raising=False)
    else:
        monkeypatch.setenv("OLLAMA_HOST", value)
    assert ollama_host() == expected


def test_config_uses_ollama_variables(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_HOST", "127.0.0.1:11500")
    monkeypatch.setenv("OLLAMA_CHAT_MODEL", "qwen3:4b")
    config = load_config()
    assert config.base_url == "http://127.0.0.1:11500/v1" and config.chat_model == "qwen3:4b"


def test_behavior_file_is_the_nutriscope_role():
    behavior = load_behavior()
    assert behavior.temperature == 0
    assert "NutriScope" in behavior.prompt and "chercher_produit" in behavior.prompt
    assert not behavior.prompt.startswith("TEMPERATURE")


# --- garde-fous ------------------------------------------------------------------

@pytest.mark.parametrize("question", [
    "Je suis diabétique, puis-je manger du Nutella ?",
    "Je suis enceinte, ce fromage est-il conseillé ?",
    "Quel produit pour faire baisser mon cholestérol ?",
    "J'ai un traitement contre l'hypertension, je peux manger salé ?",
])
def test_medical_questions_are_refused_in_code(question):
    assert medical_refusal(question)


@pytest.mark.parametrize("question", [
    "Quel est le Nutri-Score du Nutella ?",
    "Compare les biscuits Prince et les Pépito",
    "Combien de sucre dans une goutte de sirop ?",
])
def test_food_questions_pass_the_medical_filter(question):
    assert medical_refusal(question) is None


def test_numbers_must_come_from_the_facts():
    facts = [{"nutriments": {"sucres": 56.3, "sel": 0.107, "kcal": 539}}]
    assert unsupported_numbers("56,3 g de sucres et 539 kcal pour 100 g.", facts) == []
    assert unsupported_numbers("Environ 56 g de sucres, 0,11 g de sel.", facts) == []      # arrondis d'affichage
    assert unsupported_numbers("Il contient 2 g de fibres.", facts) == ["2"]               # valeur inventée
    assert unsupported_numbers("Soit 12 g de plus que l'autre.", facts) == ["12"]          # valeur calculée
    assert unsupported_numbers("J'ai trouvé 3 produits.", facts) == []                     # un compte


# --- boucle --------------------------------------------------------------------------

def test_medical_refusal_does_not_call_the_model():
    assistant, client = make_assistant([])
    answer = assistant.ask("Je suis diabétique, puis-je manger du Nutella ?")
    assert answer.outcome == "refused_medical" and client.requests == []


def test_tool_call_then_grounded_answer():
    assistant, client = make_assistant([
        tool_reply("chercher_produit", {"nom": "pâte à tartiner"}),
        text_reply("Nutri-Score E, 56,3 g de sucres pour 100 g. Données : Open Food Facts."),
    ])
    answer = assistant.ask("Quel est le Nutri-Score de la pâte à tartiner ?")
    assert answer.outcome == "answered" and answer.model_calls == 2
    assert answer.tool_calls[0].result["statut"] == "ok"
    tool_message = client.requests[1]["messages"][-1]
    assert tool_message["role"] == "tool" and tool_message["tool_call_id"] == "call_1"


def test_invalid_tool_request_is_reported_to_the_model():
    assistant, client = make_assistant([
        tool_reply("chercher_produit", '{"nom": "x", "rayon": "y"}'),
        tool_reply("effacer_tout", "{}", call_id="call_2"),
        text_reply("Je n'ai pas trouvé ce produit."),
    ])
    answer = assistant.ask("Cherche x")
    assert [t.result.keys() for t in answer.tool_calls] == [{"erreur"}, {"erreur"}]
    assert answer.outcome == "answered"


def test_loop_cannot_run_forever():
    replies = [tool_reply("chercher_produit", {"nom": "biscuit"}, call_id=f"c{i}") for i in range(3)]
    replies.append(text_reply("Plusieurs biscuits correspondent."))
    assistant, client = make_assistant(replies, max_tool_rounds=3)
    answer = assistant.ask("biscuit ?")
    assert answer.model_calls == 4
    assert "tools" not in client.requests[-1]          # dernier tour : le modèle doit répondre en texte


def test_invented_number_gets_one_review_then_fallback():
    assistant, _ = make_assistant([
        tool_reply("chercher_produit", {"code": "3000000000017"}),
        text_reply("Ce produit contient 4 g de fibres."),
        text_reply("Il contient 4 g de fibres, j'insiste."),
    ])
    answer = assistant.ask("Combien de fibres dans 3000000000017 ?")
    assert answer.outcome == "fallback" and "4" in answer.unsupported_numbers
    assert "4 g" not in answer.text and "Nutri-Score E" in answer.text


def test_review_round_can_fix_the_answer():
    assistant, _ = make_assistant([
        tool_reply("chercher_produit", {"code": "3000000000017"}),
        text_reply("Ce produit contient 4 g de fibres."),
        text_reply("La teneur en fibres n'est pas renseignée dans la fiche."),
    ])
    answer = assistant.ask("Combien de fibres dans 3000000000017 ?")
    assert answer.outcome == "reviewed"


def test_model_down_gives_a_message_not_an_exception():
    assistant, _ = make_assistant([ConnectionError("refused")])
    answer = assistant.ask("Nutri-Score du Nutella ?")
    assert answer.outcome.startswith("error") and answer.text


def test_unverified_scan_is_always_announced():
    assistant, _ = make_assistant([text_reply("Il contient 10,6 g de sucres pour 100 ml.")])
    assistant.scanner = lambda image: {"statut": "non_verifie", "nutriments": {"sucres": 10.6}, "produit": {}}
    answer = assistant.ask("C'est sucré ?", image=b"photo")
    assert answer.text.startswith("Lecture de l'étiquette non vérifiée")
