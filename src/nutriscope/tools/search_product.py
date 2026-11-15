"""
Plugin ``chercher_produit`` : le seul outil dont le contrat est imposé (TP 18, repris aux TP 21 et 23).

Arguments (objet JSON écrit par le modèle) :

| Argument | Type                    | Rôle                                                    |
| -------- | ----------------------- | ------------------------------------------------------- |
| `nom`    | texte, facultatif       | nom ou partie du nom ; casse et accents ignorés         |
| `code`   | texte, facultatif       | code-barres exact ; prime sur `nom`                     |
| `limite` | entier 1 à 5, facultatif | nombre maximal de fiches renvoyées (3 par défaut)      |

Au moins `nom` ou `code` ; aucun autre argument. Résultat :

    {"statut": "ok" | "ambigu" | "introuvable", "total": <nombre trouvé>, "produits": [<fiche>, ...]}

Arguments invalides -> {"erreur": "<explication>"}, jamais d'exception.
Le nom cherche aussi dans la marque (« prince lu » trouve les Prince de LU).
"""

from __future__ import annotations

import re
from typing import Any

from ..catalog import Catalog, build_fiche, search_words
from .base import Tool, ToolContext, ToolError

ALLOWED_ARGUMENTS = ("nom", "code", "limite")
DEFAULT_LIMIT = 3
MAX_LIMIT = 5
MAX_NAME_LENGTH = 120
BARCODE = re.compile(r"^\d{8,14}$")


class SearchProductTool(Tool):
    name = "chercher_produit"
    description = (
        "Cherche des produits alimentaires dans le catalogue NutriScope (données Open Food Facts) et rend "
        "leur fiche : Nutri-Score et valeurs nutritionnelles pour 100 g. Donner `code` (code-barres exact, "
        "prioritaire) ou `nom` (nom ou partie du nom, marque possible). Statut `ambigu` : plusieurs produits, "
        "faire préciser l'utilisateur. Une valeur null est inconnue (jamais 0)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "nom": {"type": "string", "description": "Nom ou partie du nom du produit, ex. « nutella »"},
            "code": {"type": "string", "description": "Code-barres exact (8 à 13 chiffres), ex. « 3017620422003 »"},
            "limite": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT,
                       "description": "Nombre maximal de fiches renvoyées (3 par défaut)"},
        },
        "additionalProperties": False,
    }

    def __init__(self, catalog: Catalog):
        self.catalog = catalog

    def validate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        unknown = sorted(set(arguments) - set(ALLOWED_ARGUMENTS))
        if unknown:
            raise ToolError(f"unknown argument(s): {', '.join(map(str, unknown))[:80]}; "
                            f"allowed: {', '.join(ALLOWED_ARGUMENTS)}")

        name = arguments.get("nom")
        if name is not None:
            if not isinstance(name, str):
                raise ToolError("`nom` must be a string")
            name = name.strip() or None
            if name and len(name) > MAX_NAME_LENGTH:
                raise ToolError(f"`nom` too long (max {MAX_NAME_LENGTH} characters)")
            if name and not search_words(name):
                raise ToolError("`nom` contains no letter or digit")

        code = arguments.get("code")
        if code is not None:
            if not isinstance(code, str):
                raise ToolError("`code` must be a string of digits, e.g. \"3017620422003\"")
            code = re.sub(r"[\s-]", "", code) or None
            if code and not BARCODE.match(code):
                raise ToolError("`code` must contain 8 to 14 digits only")

        if not name and not code:
            raise ToolError("give at least `nom` or `code`")

        limit = arguments.get("limite", DEFAULT_LIMIT)
        if limit is None:
            limit = DEFAULT_LIMIT
        if isinstance(limit, bool) or not isinstance(limit, int):
            raise ToolError(f"`limite` must be an integer from 1 to {MAX_LIMIT}")
        if not 1 <= limit <= MAX_LIMIT:
            raise ToolError(f"`limite` = {limit} is out of bounds (1 to {MAX_LIMIT})")
        return {"nom": name, "code": code, "limite": limit}

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = arguments["limite"]
        if arguments["code"]:                       # le code-barres prime sur le nom
            rows = self.catalog.find_by_code(arguments["code"])
            total = len(rows)
        else:
            total, rows = self.catalog.search_by_name(search_words(arguments["nom"]), limit)
        products = [build_fiche(row) for row in rows[:limit]]
        status = "introuvable" if total == 0 else "ok" if total == 1 else "ambigu"
        return {"statut": status, "total": total, "produits": products}


def create_tool(context: ToolContext) -> SearchProductTool | None:
    return SearchProductTool(context.catalog) if context.catalog is not None else None
