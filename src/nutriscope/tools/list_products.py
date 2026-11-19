"""
Plugin ``lister_produits`` : plusieurs produits d'un type, filtrés et classés (questions de liste).

``chercher_produit`` sert à désigner **un** produit : plusieurs correspondances y sont ``ambigu`` et
l'assistant demande lequel. « Quels biscuits sont bien notés ? » ne désigne aucun produit : c'est
une liste, qui passe par cet outil et n'est jamais ``ambigu``. Contrat propre à l'équipe :

| Argument         | Type                         | Rôle                                                    |
| ---------------- | ---------------------------- | ------------------------------------------------------- |
| `mots`           | liste de 1 à 5 textes, obligatoire | mots-clés du type de produit, ex. ["yaourt", "nature"] |
| `nutriscore_max` | lettre A à E, facultatif     | Nutri-Score le moins bon accepté (« B » : A et B)       |
| `tri`            | voir ``SORTS``, facultatif   | classement (`nutriscore` par défaut : le meilleur d'abord) |
| `limite`         | entier 1 à 5, facultatif     | nombre maximal de fiches renvoyées (5 par défaut)       |

Aucun autre argument. Résultat :

    {"statut": "ok" | "introuvable", "total": <nombre trouvé>, "tri": <tri>, "ordre": <sens>,
     "produits": [<fiche>, ...]}

Des mots-clés plutôt qu'une phrase : c'est le modèle, qui comprend la langue, qui écarte articles et
prépositions (« céréales du petit-déjeuner » -> ["céréales", "petit-déjeuner"]). Une fiche doit
contenir chaque mot ; aucune liste de mots vides n'est donc nécessaire. Mesuré le 19/11/2026 : sur
10 questions de liste, aucun article ni préposition envoyé, mêmes produits qu'avec l'ancienne liste.
Leur fréquence ne permettait pas de les repérer : « du » est dans 2,5 % des fiches, moins que
« biscuits » (8,7 %).

Chaque fiche est son ``rang`` (1 = premier du classement) suivi d'une fiche de ``chercher_produit``
(``build_fiche``) réduite à ``LIST_FIELDS`` : avec
le prompt et les trois outils, cinq fiches complètes dépassaient le contexte de 4 096 tokens du
modèle local (mesuré). Le classement porte sur les produits du catalogue NutriScope (échantillon
Open Food Facts), pas sur tout le marché.
Arguments invalides -> {"erreur": "<explication>"}.
"""

from __future__ import annotations

from typing import Any

from ..catalog import GRADES, SHEET_NUTRIENTS, build_fiche, search_words
from .base import Tool, ToolContext, ToolError

ALLOWED_ARGUMENTS = ("mots", "nutriscore_max", "tri", "limite")
DEFAULT_LIMIT = 5
MAX_LIMIT = 5
MAX_KEYWORDS = 5
MAX_KEYWORD_LENGTH = 40
DEFAULT_SORT = "nutriscore"
LIST_FIELDS = ("code", "nom", "marque", "nutriscore", "categorie", "nutriments")
# tri -> (champ des fiches de l'index, du plus grand au plus petit ?)
SORTS = {
    "nutriscore": ("nutriscore_score", False),
    **{key: (column, key in ("fibres", "proteines")) for key, column in SHEET_NUTRIENTS.items()},
}


def compact_fiche(row: dict[str, Any], rank: int) -> dict[str, Any]:
    """Fiche réduite, précédée de son rang : sans lui, le modèle 4B réordonnait parfois la liste (mesuré)."""
    fiche = build_fiche(row)
    return {"rang": rank, **{key: fiche[key] for key in LIST_FIELDS}}


class ListProductsTool(Tool):
    name = "lister_produits"
    description = (
        "Liste et classe plusieurs produits d'un même type du catalogue NutriScope (« quels biscuits sont "
        "bien notés ? »). Pas pour un produit précis (chercher_produit)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "mots": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": MAX_KEYWORDS,
                     "description": "Mots qui désignent le type de produit, ex. [\"yaourt\", \"nature\"]"},
            "nutriscore_max": {"type": "string", "enum": [grade.upper() for grade in GRADES],
                               "description": "« B » : A et B seulement"},
            "tri": {"type": "string", "enum": list(SORTS),
                    "description": "nutriscore par défaut ; fibres, proteines : le plus d'abord ; sinon le moins"},
            "limite": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT},
        },
        "required": ["mots"],
        "additionalProperties": False,
    }

    def __init__(self, catalog):
        self.catalog = catalog      # objet qui offre list_products(...) (RagIndex)

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - set(ALLOWED_ARGUMENTS))
        if unknown:
            raise ToolError(f"unknown argument(s): {', '.join(map(str, unknown))[:80]}; "
                            f"allowed: {', '.join(ALLOWED_ARGUMENTS)}")
        keywords = arguments.get("mots")
        if (not isinstance(keywords, list) or not 1 <= len(keywords) <= MAX_KEYWORDS
                or not all(isinstance(word, str) and word.strip() for word in keywords)):
            raise ToolError(f"`mots` is required: a list of 1 to {MAX_KEYWORDS} non-empty strings, "
                            "e.g. [\"yaourt\", \"nature\"]")
        keywords = [" ".join(word.split()) for word in keywords]
        if any(len(word) > MAX_KEYWORD_LENGTH for word in keywords):
            raise ToolError(f"each keyword in `mots` must be at most {MAX_KEYWORD_LENGTH} characters")
        if not search_words(" ".join(keywords)):
            raise ToolError("`mots` contains no letter or digit")

        worst = arguments.get("nutriscore_max")
        if worst is not None:
            if not isinstance(worst, str) or worst.strip().lower() not in GRADES:
                raise ToolError("`nutriscore_max` must be one letter from A to E")
            worst = worst.strip().upper()

        sort = arguments.get("tri") or DEFAULT_SORT
        if sort not in SORTS:
            raise ToolError(f"`tri` must be one of: {', '.join(SORTS)}")

        limit = arguments.get("limite", DEFAULT_LIMIT)
        if limit is None:
            limit = DEFAULT_LIMIT
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
            raise ToolError(f"`limite` must be an integer from 1 to {MAX_LIMIT}")
        return {"mots": keywords, "nutriscore_max": worst, "tri": sort, "limite": limit}

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        worst = arguments["nutriscore_max"]
        grades = list(GRADES[:GRADES.index(worst.lower()) + 1]) if worst and worst != "E" else None
        field, descending = SORTS[arguments["tri"]]
        query = " ".join(arguments["mots"])          # texte vectorisé pour le repli sémantique
        total, rows = self.catalog.list_products(search_words(query), query, grades, field, descending,
                                                 arguments["limite"])
        order = ("meilleur d'abord" if arguments["tri"] == "nutriscore"
                 else "le plus d'abord" if descending else "le moins d'abord")
        return {"statut": "ok" if total else "introuvable", "total": total, "tri": arguments["tri"],
                "ordre": order, "produits": [compact_fiche(row, rank) for rank, row in enumerate(rows, 1)]}


def create_tool(context: ToolContext) -> ListProductsTool | None:
    catalog = context.catalog
    return ListProductsTool(catalog) if hasattr(catalog, "list_products") else None
