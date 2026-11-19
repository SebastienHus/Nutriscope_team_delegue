"""
Les outils de l'assistant, sous forme de plugins.

Chaque module de ce paquet (sauf ceux qui commencent par ``_`` et ``base``) est un plugin : il
définit une sous-classe de ``Tool`` et une fabrique ``create_tool(context)``.
``ToolRegistry.discover`` les importe tous : ajouter un outil, c'est déposer un fichier ici.

    index = RagIndex.from_env()                              # nutriscope.rag.retriever
    registry = ToolRegistry.discover(ToolContext(catalog=index, documents=index))
    registry.schemas()                                       # déclarations envoyées au modèle
    registry.run("chercher_produit", '{"nom": "nutella"}')   # ne lève jamais d'exception

Plugins disponibles aujourd'hui :

| Module            | Outil               | Rôle                                                              |
| ----------------- | ------------------- | ----------------------------------------------------------------- |
| `search_product`  | `chercher_produit`  | fiches produits du catalogue (contrat du TP 18), index du RAG     |
| `list_products`   | `lister_produits`   | produits d'un type, filtrés et classés (questions de liste)        |
| `search_document` | `chercher_document` | passages des documents de référence (Nutri-Score, repères PNNS)   |
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Any, Iterable

from .base import Tool, ToolContext, ToolError, parse_arguments

__all__ = ["Tool", "ToolContext", "ToolError", "ToolRegistry", "parse_arguments"]

log = logging.getLogger(__name__)
_NOT_PLUGINS = {"base"}


class ToolRegistry:
    """Les outils que le modèle peut appeler. Tout autre outil demandé est refusé."""

    def __init__(self, tools: Iterable[Tool] = ()):
        self._tools: dict[str, Tool] = {}
        for tool in tools:
            if tool.name in self._tools:
                raise ValueError(f"two plugins declare the tool {tool.name!r}")
            self._tools[tool.name] = tool

    @classmethod
    def discover(cls, context: ToolContext | None = None, enabled: Iterable[str] | None = None) -> "ToolRegistry":
        """Importe tous les plugins du paquet ; ``enabled`` restreint les outils par nom."""
        context = context or ToolContext()
        wanted = set(enabled) if enabled is not None else None
        tools = []
        for module_info in pkgutil.iter_modules(__path__):
            if module_info.name.startswith("_") or module_info.name in _NOT_PLUGINS:
                continue
            module = importlib.import_module(f"{__name__}.{module_info.name}")
            factory = getattr(module, "create_tool", None)
            if factory is None:
                log.warning("module %s has no create_tool(context): ignored", module_info.name)
                continue
            tool = factory(context)
            if tool is not None and (wanted is None or tool.name in wanted):
                tools.append(tool)
        return cls(tools)

    @property
    def names(self) -> list[str]:
        return sorted(self._tools)

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def run(self, name: Any, raw_arguments: Any) -> dict[str, Any]:
        """Exécute un outil demandé par le modèle. Outil inconnu ou arguments invalides -> {"erreur": ...}."""
        if not isinstance(name, str) or name not in self._tools:
            shown = name[:40] if isinstance(name, str) else type(name).__name__
            return {"erreur": f"unknown tool {shown!r}; available tools: {', '.join(self.names)}"}
        return self._tools[name](raw_arguments)
