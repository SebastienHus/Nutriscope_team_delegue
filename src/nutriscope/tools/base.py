"""
Contrat des plugins : les outils de l'assistant.

Un plugin est un module du paquet ``nutriscope.tools`` qui définit une sous-classe de ``Tool``
et une fabrique ``create_tool(context)``. Le registre (``nutriscope.tools.ToolRegistry``) découvre
les plugins en parcourant le paquet : ajouter un outil, c'est ajouter un fichier, rien d'autre.

Tout ce qu'écrit le modèle (nom d'outil, arguments) est une donnée non fiable. Un outil :

1. lit les arguments bruts (texte JSON écrit par le modèle), sans ``eval`` ;
2. les valide (``validate``) avant toute action ;
3. s'exécute et rend un dictionnaire sérialisable en JSON.

Un outil ne lève jamais d'exception : des arguments invalides ou une panne deviennent
``{"erreur": "<explication>"}``, renvoyé au modèle pour qu'il se corrige.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

log = logging.getLogger(__name__)

MAX_ARGUMENTS_LENGTH = 2_000   # caractères de JSON brut acceptés du modèle


class ToolError(ValueError):
    """Arguments invalides. Signalés au modèle par {"erreur": ...}, jamais levés vers l'appelant."""


@dataclass
class ToolContext:
    """Ce dont les plugins peuvent avoir besoin. Un plugin privé d'une dépendance rend None depuis ``create_tool``."""

    catalog: Any = None
    extra: dict[str, Any] = field(default_factory=dict)


def parse_arguments(raw: str | dict | None) -> dict[str, Any]:
    """Arguments du modèle -> dict. JSON uniquement : rien de ce qu'écrit le modèle n'est jamais évalué."""
    if raw is None or raw == "":
        return {}
    if isinstance(raw, dict):
        return dict(raw)
    if not isinstance(raw, str):
        raise ToolError("arguments must be a JSON object")
    if len(raw) > MAX_ARGUMENTS_LENGTH:
        raise ToolError(f"arguments too long ({len(raw)} characters, max {MAX_ARGUMENTS_LENGTH})")
    try:
        arguments = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ToolError(f"unreadable JSON arguments: {exc.msg}") from None
    if not isinstance(arguments, dict):
        raise ToolError("arguments must be a JSON object, e.g. {\"nom\": \"nutella\"}")
    return arguments


class Tool(ABC):
    """Classe de base de tous les plugins."""

    name: ClassVar[str]
    description: ClassVar[str]
    parameters: ClassVar[dict[str, Any]]   # schéma JSON des arguments, montré au modèle

    def schema(self) -> dict[str, Any]:
        """Déclaration de l'outil au format OpenAI / Ollama."""
        return {"type": "function",
                "function": {"name": self.name, "description": self.description, "parameters": self.parameters}}

    @abstractmethod
    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Arguments vérifiés et normalisés. Lève ToolError s'ils sont invalides."""

    @abstractmethod
    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Exécute l'outil sur des arguments validés."""

    def __call__(self, raw_arguments: str | dict | None) -> dict[str, Any]:
        """Arguments non fiables en entrée, résultat sérialisable en JSON en sortie. Ne lève jamais d'exception."""
        try:
            arguments = self.validate(parse_arguments(raw_arguments))
        except ToolError as exc:
            return {"erreur": str(exc)}
        try:
            return self.execute(arguments)
        except Exception as exc:  # base arrêtée, délai dépassé... le modèle est prévenu, l'appelant n'est pas interrompu
            log.exception("tool %s failed", self.name)
            return {"erreur": f"tool unavailable ({type(exc).__name__}), try again later"}
