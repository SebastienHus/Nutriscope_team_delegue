"""
Doublures de test pour l'assistant et le scanner : un FAUX client de modèle et un petit catalogue en mémoire.

Rien ici n'est un vrai modèle ni de vraies données : ces objets ne font qu'exercer le code
(validation, bornes de la boucle, relecture). Les démonstrations tournent sur le vrai modèle et
le catalogue PostgreSQL.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

from nutriscope.assistant.behavior import Behavior
from nutriscope.assistant.config import LLMConfig
from nutriscope.catalog import InMemoryCatalog

FAKE_CONFIG = LLMConfig(provider="fake", base_url="http://fake/v1", api_key="fake",
                        chat_model="fake-chat", vision_model="fake-vision")
FAKE_BEHAVIOR = Behavior(prompt="Tu es un assistant de test.")

# Lignes inventées (noms de colonnes de la base), pour les tests unitaires uniquement
FAKE_ROWS = [
    {"code": "3000000000017", "name": "Pâte à tartiner noisette", "brands": "marque-a", "nutriscore_grade": "e",
     "nutriscore": 26, "energy_kcal_100g": 539, "energy_100g": 2252, "fat_100g": 30.9, "saturated_fat_100g": 10.6,
     "carbohydrates_100g": 57.5, "sugars_100g": 56.3, "fiber_100g": None, "proteins_100g": 6.3, "salt_100g": 0.107,
     "pnns_group_1": "Sugary snacks", "labels": "en:no-palm-oil-free"},
    {"code": "3000000000024", "name": "Biscuit fourré chocolat", "brands": "marque-b", "nutriscore_grade": "d",
     "nutriscore": 15, "energy_kcal_100g": 466, "energy_100g": 1960, "fat_100g": 17.0, "saturated_fat_100g": 5.4,
     "carbohydrates_100g": 68.0, "sugars_100g": 32.0, "fiber_100g": 4.1, "proteins_100g": 6.4, "salt_100g": 0.5,
     "pnns_group_1": "Sugary snacks"},
    {"code": "3000000000031", "name": "Biscuit fourré vanille", "brands": "marque-b", "nutriscore_grade": "d",
     "nutriscore": 14, "energy_kcal_100g": 470, "energy_100g": 1975, "fat_100g": 17.5, "saturated_fat_100g": 5.0,
     "carbohydrates_100g": 69.0, "sugars_100g": 30.0, "fiber_100g": 2.0, "proteins_100g": 6.0, "salt_100g": 0.4,
     "pnns_group_1": "Sugary snacks"},
    {"code": "3000000000048", "name": "Yaourt nature", "brands": "marque-c", "nutriscore_grade": None,
     "nutriscore": None, "energy_kcal_100g": 60, "energy_100g": 251, "fat_100g": 3.2, "saturated_fat_100g": 2.1,
     "carbohydrates_100g": 4.5, "sugars_100g": 4.5, "fiber_100g": 0, "proteins_100g": 4.0, "salt_100g": None,
     "pnns_group_1": "Milk and dairy products"},
]


def fake_catalog() -> InMemoryCatalog:
    return InMemoryCatalog(FAKE_ROWS)


def text_reply(content: str) -> dict[str, Any]:
    return {"content": content}


def tool_reply(name: str, arguments: dict | str, call_id: str = "call_1") -> dict[str, Any]:
    raw = arguments if isinstance(arguments, str) else json.dumps(arguments)
    return {"content": "", "tool_calls": [(call_id, name, raw)]}


class FakeChatClient:
    """FAUX client compatible OpenAI : rejoue des réponses écrites d'avance et enregistre les requêtes."""

    def __init__(self, replies: list[dict[str, Any]], repeat_last: bool = False):
        self.replies = list(replies)
        self.repeat_last = repeat_last
        self.requests: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **request: Any) -> SimpleNamespace:
        self.requests.append(request)
        if not self.replies:
            raise AssertionError("the fake client ran out of scripted replies")
        reply = self.replies[0] if self.repeat_last and len(self.replies) == 1 else self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        calls = [SimpleNamespace(id=cid, function=SimpleNamespace(name=name, arguments=args))
                 for cid, name, args in reply.get("tool_calls", [])]
        message = SimpleNamespace(content=reply.get("content", ""), tool_calls=calls or None)
        return SimpleNamespace(choices=[SimpleNamespace(message=message, finish_reason=reply.get("finish_reason", "stop"))],
                               usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))
