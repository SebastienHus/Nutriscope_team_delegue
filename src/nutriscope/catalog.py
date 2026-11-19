"""
Accès en lecture seule au catalogue de produits, et fiche produit commune à tous les outils.

Deux implémentations de la même interface :

- ``nutriscope.rag.retriever.RagIndex`` : l'index vectoriel Chroma (fiches du RAG). C'est celle
  qu'utilisent l'assistant et le scanner (ADR 0005). La recherche SQL du TP 18 a été retirée : la
  base PostgreSQL reste chargée par le pipeline, mais les outils ne la lisent plus ;
- ``InMemoryCatalog`` : une liste de lignes en mémoire, réservée aux tests unitaires et au
  développement hors ligne (jamais à la démonstration, qui se fait sur des données réelles).

Toutes rendent des lignes brutes (noms de colonnes de la base) ; ``build_fiche`` en fait la
fiche imposée par le contrat du TP 18. Une valeur inconnue vaut ``None``, jamais 0.

Données : © Open Food Facts contributors — ODbL.
"""

from __future__ import annotations

import math
import re
from decimal import Decimal
from typing import Any, Iterable, Protocol

# ----------------------------------------------------------------------------
# Fiche produit
# ----------------------------------------------------------------------------

# Clé du contrat -> colonne de la base (table `nutrition`), valeurs pour 100 g
SHEET_NUTRIENTS = {
    "kcal": "energy_kcal_100g",
    "lipides": "fat_100g",
    "satures": "saturated_fat_100g",
    "sucres": "sugars_100g",
    "sel": "salt_100g",
    "fibres": "fiber_100g",
    "proteines": "proteins_100g",
}
# Valeurs en plus (hors contrat) : pour expliquer un score, et pour le scanner d'étiquettes
EXTRA_NUTRIENTS = {
    "kj": "energy_100g",
    "glucides": "carbohydrates_100g",
    "fruits_legumes_pct": "fruits_vegetables_legumes_100g",
}
GRADES = ("a", "b", "c", "d", "e")

DETAIL_COLUMNS = (
    "code", "name", "quantity", "pnns_group_1", "pnns_group_2", "brands", "labels",
    "nutriscore", "nutriscore_grade", "nova_group",
    *SHEET_NUTRIENTS.values(), *EXTRA_NUTRIENTS.values(),
)


def to_number(value: Any) -> float | None:
    """Valeur de la base -> float, ou None si inconnue (NULL, NaN, pas un nombre)."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, Decimal):
        value = float(value)
    if isinstance(value, (int, float)) and math.isfinite(value):
        return round(float(value), 3)
    return None


def _split_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return [str(part) for part in value if part]


def build_fiche(row: dict[str, Any]) -> dict[str, Any]:
    """Ligne brute du catalogue -> fiche produit (contrat du TP 18, plus quelques clés en plus)."""
    nutrients = {key: to_number(row.get(column)) for key, column in SHEET_NUTRIENTS.items()}
    grade = row.get("nutriscore_grade")
    grade = grade.upper() if isinstance(grade, str) and grade.lower() in GRADES else None
    points = row.get("nutriscore")
    nova = row.get("nova_group")
    return {
        "code": str(row["code"]),
        "nom": row.get("name"),
        "marque": ", ".join(_split_list(row.get("brands"))) or None,
        "nutriscore": grade,
        "nutriments": nutrients,
        "donnees_incompletes": grade is None or any(v is None for v in nutrients.values()),
        # Clés en plus, permises par le contrat
        "score_nutriscore": int(points) if to_number(points) is not None else None,
        "nutriments_complementaires": {key: to_number(row.get(column)) for key, column in EXTRA_NUTRIENTS.items()},
        "rayon": row.get("pnns_group_1"),
        "categorie": row.get("pnns_group_2"),
        "quantite": row.get("quantity"),
        "nova": int(nova) if to_number(nova) is not None else None,
        "labels": _split_list(row.get("labels")),
    }


# ----------------------------------------------------------------------------
# Normalisation du texte (casse et accents ignorés), identique en Python et en SQL
# ----------------------------------------------------------------------------

_ACCENT_GROUPS = {"a": "àáâãäåā", "c": "çćč", "e": "èéêëēėę", "i": "ìíîïī", "n": "ñń", "o": "òóôõöøōœ",
                  "u": "ùúûüū", "y": "ýÿ", "z": "ž"}
_ACCENTED = "".join(_ACCENT_GROUPS.values())
_PLAIN = "".join(plain * len(accented) for plain, accented in _ACCENT_GROUPS.items())
_TRANSLATION = str.maketrans(_ACCENTED, _PLAIN)
_WORD = re.compile(r"[a-z0-9]+")
MAX_SEARCH_WORDS = 8
# Un mot d'au moins 3 caractères est cherché n'importe où dans le texte (« tella » trouve « Nutella »,
# index trigrammes pg_trgm). Plus court, il n'a pas de trigramme : il doit alors commencer un mot
# (« lu » trouve « LU Prince » et « Lulu », pas « Valu »), recherche servie par l'index plein texte.
SHORT_WORD_LENGTH = 3
# Au-delà, la recherche est trop vague : classer des dizaines de milliers de produits dépasserait le
# délai par requête, et aucun utilisateur ne choisit parmi eux. Mesuré sur l'extrait complet :
# « eau » (15 522 produits) 1,8 s, « chocolat » (39 930) 2,4 s, « de » (200 059) 4 s.
MAX_MATCHES = 20_000


class TooManyMatches(Exception):
    """Recherche trop vague : plus de ``MAX_MATCHES`` produits correspondent."""

    def __init__(self, at_least: int):
        super().__init__(f"more than {at_least} matching products")
        self.at_least = at_least


def normalize_text(text: str) -> str:
    """
    Minuscules, accents retirés : même correspondance que la fonction SQL ``normalize_text``
    de ``schema_nutriscope.sql`` (sur laquelle portent les index de recherche).
    """
    return text.lower().translate(_TRANSLATION)


def is_short_word(word: str) -> bool:
    """Mot trop court pour une recherche par sous-chaîne : il doit commencer un mot du texte."""
    return len(word) < SHORT_WORD_LENGTH


def word_matches(word: str, text: str) -> bool:
    """``word`` (déjà normalisé) figure dans ``text`` : sous-chaîne, ou début de mot s'il est court."""
    text = normalize_text(text)
    if is_short_word(word):
        return any(token.startswith(word) for token in _WORD.findall(text))
    return word in text


def search_words(text: str) -> list[str]:
    """Mots distincts d'une recherche (lettres et chiffres seulement, donc sans danger dans un motif LIKE)."""
    return list(dict.fromkeys(_WORD.findall(normalize_text(text))))[:MAX_SEARCH_WORDS]   # sans doublon


def code_variants(code: str) -> list[str]:
    """Un UPC-A à 12 chiffres est aussi stocké comme un EAN à 13 chiffres précédé d'un zéro, et inversement."""
    variants = [code]
    if len(code) == 12:
        variants.append("0" + code)
    elif len(code) == 13 and code.startswith("0"):
        variants.append(code[1:])
    return variants


# ----------------------------------------------------------------------------
# Interface du catalogue
# ----------------------------------------------------------------------------

class Catalog(Protocol):
    def find_by_code(self, code: str) -> list[dict[str, Any]]:
        """Lignes dont le code-barres est ``code`` (0 ou 1 en pratique)."""

    def search_by_name(self, words: list[str], limit: int,
                       query: str | None = None) -> tuple[int, list[dict[str, Any]]]:
        """
        (nombre total de produits trouvés, ``limit`` meilleures lignes). Chaque mot doit figurer
        dans le nom ou une marque (``word_matches`` : sous-chaîne, ou début de mot s'il est court).
        Peut lever ``TooManyMatches`` (recherche trop vague). ``query`` : le nom tel qu'écrit,
        accents compris (vectorisé par la recherche sémantique).
        """


def _rank_key(row: dict[str, Any], full: str) -> tuple:
    """
    Ordre des résultats : nom exact, puis nom qui commence par la recherche, puis
    Nutri-Score connu, puis fiche la plus complète (entre homonymes, la fiche de référence d'un
    produit est bien mieux renseignée que ses doublons), puis nom le plus court et code.
    """
    name = normalize_text(row.get("name") or "")
    grade = row.get("nutriscore_grade")
    completeness = to_number(row.get("completeness"))
    return (name != full, not name.startswith(full), grade not in GRADES,
            -(completeness if completeness is not None else -1.0), len(name), str(row["code"]))


class InMemoryCatalog:
    """Catalogue en mémoire. Réservé aux tests unitaires et au développement hors ligne."""

    def __init__(self, rows: Iterable[dict[str, Any]]):
        self.rows = [dict(row) for row in rows]

    def find_by_code(self, code: str) -> list[dict[str, Any]]:
        variants = set(code_variants(code))
        return [row for row in self.rows if str(row["code"]) in variants]

    def search_by_name(self, words: list[str], limit: int,
                       query: str | None = None) -> tuple[int, list[dict[str, Any]]]:
        def haystack(row):
            return normalize_text(f"{row.get('name') or ''} {row.get('brands') or ''}")

        matches = [row for row in self.rows if all(word_matches(word, haystack(row)) for word in words)]
        if len(matches) > MAX_MATCHES:
            raise TooManyMatches(MAX_MATCHES)
        matches.sort(key=lambda row: _rank_key(row, " ".join(words)))
        return len(matches), matches[:limit]


def default_catalog() -> Catalog:
    """Le catalogue de l'assistant et du scanner : l'index du RAG (ADR 0005)."""
    from .rag.retriever import RagIndex

    return RagIndex.from_env()
