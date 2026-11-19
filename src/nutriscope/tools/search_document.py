"""
Plugin ``chercher_document`` : passages des documents de référence (Nutri-Score, repères PNNS).

Contrat propre à l'équipe (le brief n'impose que ``chercher_produit``), sur le même modèle :

| Argument   | Type                     | Rôle                                                |
| ---------- | ------------------------ | --------------------------------------------------- |
| `question` | texte, obligatoire       | la question de l'utilisateur, reformulée au besoin  |
| `limite`   | entier 1 à 5, facultatif | nombre maximal de passages renvoyés (3 par défaut)  |

Aucun autre argument. Résultat :

    {"statut": "ok" | "introuvable", "total": <nombre de passages>,
     "passages": [{"texte", "source", "titre", "editeur", "url", "page", "mis_a_jour", "pertinence"}]}

``introuvable`` : aucun passage assez proche de la question (similarité sous
``nutriscope.rag.retriever.DOCUMENT_THRESHOLD``). Le texte d'un passage est le texte d'origine du
document, à citer avec sa source et sa date. Arguments invalides -> {"erreur": "<explication>"}.
"""

from __future__ import annotations

from typing import Any

from .base import Tool, ToolContext, ToolError

ALLOWED_ARGUMENTS = ("question", "limite")
DEFAULT_LIMIT = 3
MAX_LIMIT = 5
MAX_QUESTION_LENGTH = 300


class SearchDocumentTool(Tool):
    name = "chercher_document"
    description = (
        "Cherche dans les documents de référence de NutriScope (Nutri-Score : fonctionnement, calcul, "
        "réglementation ; repères nutritionnels officiels) les passages qui répondent à une question générale, "
        "qui ne porte pas sur un produit précis. Rend le texte d'origine de chaque passage avec sa source "
        "(éditeur, titre, page, date) à citer. Statut `introuvable` : aucun document ne traite la question."
    )
    parameters = {
        "type": "object",
        "properties": {
            "question": {"type": "string",
                         "description": "La question, ex. « Comment est calculé le Nutri-Score ? »"},
            "limite": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT,
                       "description": "Nombre maximal de passages renvoyés (3 par défaut)"},
        },
        "required": ["question"],
        "additionalProperties": False,
    }

    def __init__(self, documents):
        self.documents = documents      # objet qui offre search_documents(question, limit) -> [Hit]

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - set(ALLOWED_ARGUMENTS))
        if unknown:
            raise ToolError(f"unknown argument(s): {', '.join(map(str, unknown))[:80]}; "
                            f"allowed: {', '.join(ALLOWED_ARGUMENTS)}")
        question = arguments.get("question")
        if not isinstance(question, str) or not question.strip():
            raise ToolError("`question` is required and must be a non-empty string")
        question = " ".join(question.split())
        if len(question) > MAX_QUESTION_LENGTH:
            raise ToolError(f"`question` too long (max {MAX_QUESTION_LENGTH} characters)")
        limit = arguments.get("limite", DEFAULT_LIMIT)
        if limit is None:
            limit = DEFAULT_LIMIT
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
            raise ToolError(f"`limite` must be an integer from 1 to {MAX_LIMIT}")
        return {"question": question, "limite": limit}

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        hits = self.documents.search_documents(arguments["question"], arguments["limite"])
        passages = [{
            "texte": hit.text,
            "source": hit.metadata.get("source_id"),
            "titre": hit.metadata.get("title"),
            "editeur": hit.metadata.get("publisher"),
            "url": hit.metadata.get("url"),
            "page": hit.metadata.get("page"),
            "mis_a_jour": hit.metadata.get("updated"),
            "pertinence": hit.score,
        } for hit in hits]
        return {"statut": "ok" if passages else "introuvable", "total": len(passages), "passages": passages}


def create_tool(context: ToolContext) -> SearchDocumentTool | None:
    return SearchDocumentTool(context.documents) if context.documents is not None else None
