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


# --- outil chercher_document (questions générales) ---------------------------

class FakeDocuments:
    """Faux index de documents : un passage pour « Nutri-Score », rien sinon."""

    def __init__(self):
        self.questions = []

    def search_documents(self, question, limit):
        from nutriscope.rag.search import Hit
        self.questions.append(question)
        if "nutri-score" not in question.lower():
            return []
        return [Hit("doc:viepub-ns:0001", "documents", 0.8,
                    "Un arrêté du 31 octobre 2017 fixe les modalités de calcul du score.",
                    {"source_id": "viepub-ns", "title": "Le Nutri-Score en cinq questions",
                     "publisher": "Vie publique (DILA)", "updated": "2025-03-18"})]


def make_rag_assistant(replies):
    documents = FakeDocuments()
    registry = ToolRegistry.discover(ToolContext(catalog=fake_catalog(), documents=documents))
    client = FakeChatClient(replies)
    return Assistant(registry, client=client, config=FAKE_CONFIG, behavior=FAKE_BEHAVIOR), documents


def test_document_not_found_gives_a_fixed_answer():
    assistant, _ = make_rag_assistant([
        tool_reply("chercher_document", {"question": "Combien de fruits par jour ?"}),
        text_reply("Les documents n'en parlent pas ; consultez l'INSP."),   # ajout de mémoire, écarté
    ])
    answer = assistant.ask("Combien de fruits par jour ?")
    assert answer.text.startswith("Les documents de référence de NutriScope ne traitent pas cette question")
    assert "INSP" not in answer.text


def test_answer_from_memory_triggers_a_document_search_by_the_agent():
    assistant, documents = make_rag_assistant([
        text_reply("Le Nutri-Score date de 2016 et compte 5 couleurs."),          # mémoire : 2016 inventé
        text_reply("Un arrêté du 31 octobre 2017 fixe son calcul. Source : Vie publique (DILA)."),
    ])
    answer = assistant.ask("D'où vient le Nutri-Score ?")
    assert documents.questions == ["D'où vient le Nutri-Score ?"]
    assert [trace.name for trace in answer.tool_calls] == ["chercher_document"]
    assert answer.outcome == "reviewed" and "2017" in answer.text


def test_fallback_quotes_the_closest_passage():
    assistant, _ = make_rag_assistant([
        tool_reply("chercher_document", {"question": "Comment est calculé le Nutri-Score ?"}),
        text_reply("Le calcul date de 1999."),
        text_reply("Le calcul date toujours de 1999."),
    ])
    answer = assistant.ask("Comment est calculé le Nutri-Score ?")
    assert answer.outcome == "fallback"
    assert "« Un arrêté du 31 octobre 2017" in answer.text and "Vie publique (DILA)" in answer.text


# --- produit ambigu : l'assistant demande, il ne choisit pas -------------------

def test_ambiguous_search_gets_a_question_not_a_choice():
    assistant, _ = make_assistant([
        tool_reply("chercher_produit", {"nom": "biscuit fourré"}),
        text_reply("Le biscuit fourré chocolat a un Nutri-Score D."),     # choix à la place de l'utilisateur
    ])
    answer = assistant.ask("Quel est le Nutri-Score du biscuit fourré ?")
    assert answer.outcome == "clarification"
    assert answer.text.startswith("Plusieurs produits correspondent à « biscuit fourré » :")
    assert "Biscuit fourré chocolat de marque-b (code 3000000000024)" in answer.text
    assert "Biscuit fourré vanille" in answer.text and answer.text.endswith("son code-barres.")


def test_a_precise_search_settles_the_ambiguity():
    assistant, _ = make_assistant([
        tool_reply("chercher_produit", {"nom": "biscuit fourré"}),
        tool_reply("chercher_produit", {"nom": "biscuit fourré vanille"}, call_id="call_2"),
        text_reply("Le biscuit fourré vanille a un Nutri-Score D. Données : Open Food Facts."),
    ])
    answer = assistant.ask("Nutri-Score du biscuit fourré vanille ?")
    assert answer.outcome == "answered" and "vanille" in answer.text


def test_comparison_asks_only_about_the_ambiguous_product():
    assistant, _ = make_assistant([
        tool_reply("chercher_produit", {"nom": "yaourt nature"}),
        tool_reply("chercher_produit", {"nom": "biscuit"}, call_id="call_2"),
        text_reply("Le yaourt est meilleur que le biscuit fourré chocolat."),
    ])
    answer = assistant.ask("Compare le yaourt nature et le biscuit")
    assert answer.outcome == "clarification"
    assert "« biscuit »" in answer.text and "« yaourt nature »" not in answer.text


class FakeListCatalog:
    """Catalogue de test qui sait aussi lister : rend toujours les deux biscuits fourrés (ou rien)."""

    def __init__(self, found=True):
        self.catalog, self.found = fake_catalog(), found

    def find_by_code(self, code):
        return self.catalog.find_by_code(code)

    def search_by_name(self, words, limit, query=None):
        return self.catalog.search_by_name(words, limit, query=query)

    def list_products(self, words, query, grades, sort, descending, limit):
        return self.catalog.search_by_name(["biscuit", "fourre"], limit) if self.found else (0, [])


@pytest.mark.parametrize("found, outcome", [(True, "answered"), (False, "clarification")])
def test_a_list_question_is_not_asked_back(found, outcome):
    registry = ToolRegistry.discover(ToolContext(catalog=FakeListCatalog(found)))
    assert "lister_produits" in registry.names
    client = FakeChatClient([
        tool_reply("chercher_produit", {"nom": "biscuit fourré"}),                         # ambigu
        tool_reply("lister_produits", {"mots": ["biscuit", "fourré"]}, call_id="call_2"),
        text_reply("Deux biscuits fourrés du catalogue NutriScope, tous deux notés D."),
    ])
    assistant = Assistant(registry, client=client, config=FAKE_CONFIG, behavior=FAKE_BEHAVIOR)
    answer = assistant.ask("Quels biscuits fourrés avez-vous ?")
    assert answer.outcome == outcome   # liste rendue : pas de question ; liste vide : l'ambiguïté reste


def test_answer_cut_by_the_token_limit_is_never_shown():
    assistant, _ = make_assistant([
        tool_reply("chercher_produit", {"nom": "yaourt nature"}),
        {"content": "Le yaourt nature a un Nutri-Score", "finish_reason": "length"},
    ])
    answer = assistant.ask("Nutri-Score du yaourt nature ?")
    assert answer.outcome == "fallback" and answer.text.startswith("Je préfère ne citer que des valeurs vérifiées")


class FakeRouter:
    def __init__(self, collection):
        self.collection = collection

    def closest_collection(self, question):
        return self.collection


def test_answer_from_memory_on_a_product_triggers_a_product_search():
    documents = FakeDocuments()
    registry = ToolRegistry.discover(ToolContext(catalog=fake_catalog(), documents=documents))
    client = FakeChatClient([
        text_reply("Le yaourt nature a 3 g de sucres."),                       # mémoire : 3 inventé
        text_reply("La teneur en sucres n'est pas renseignée. Données : Open Food Facts."),
    ])
    assistant = Assistant(registry, client=client, config=FAKE_CONFIG, behavior=FAKE_BEHAVIOR,
                          router=FakeRouter("sheets"))
    answer = assistant.ask("yaourt nature")
    assert [trace.name for trace in answer.tool_calls] == ["chercher_produit"]
    assert answer.tool_calls[0].result["statut"] == "ok" and documents.questions == []
    assert answer.outcome == "reviewed"
