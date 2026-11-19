"""
L'index vectoriel vu par les outils de l'assistant (ADR 0005).

``RagIndex`` remplace la base SQL derrière ``chercher_produit`` : il offre la même interface que
``nutriscope.catalog.Catalog`` (``find_by_code``, ``search_by_name``) et rend des lignes au format du
catalogue, que ``build_fiche`` transforme en fiche du contrat du TP 18. Le contrat de l'outil
(arguments, statuts, fiche) ne change pas ; le scanner continue de l'utiliser tel quel.
Il sert aussi ``chercher_document`` (``search_documents``) et ``lister_produits`` (``list_products``).

Recherche par nom, mesurée le 18/11/2026 sur l'index (docs/ia/rag.md) :

1. les ``CANDIDATES`` fiches les plus proches de la question (similarité cosinus) ;
2. parmi elles, celles dont le nom ou une marque contient **tous** les mots cherchés (même règle que
   la recherche SQL, ``word_matches``), quel que soit leur score : un nom court comme « prince lu »
   obtient un score faible mais une correspondance exacte ;
3. sinon (faute de frappe, autre formulation), repli sémantique : les fiches à au moins
   ``NAME_THRESHOLD`` et à moins de ``NAME_MARGIN`` de la meilleure ;
4. rien au-dessus du seuil : introuvable.

``total`` compte les fiches retenues parmi les ``CANDIDATES`` plus proches : au plus ``CANDIDATES``,
là où le SQL comptait toutes les correspondances.

Liste de produits (``list_products``), mesurée le 19/11/2026 :

1. correspondance par mots sur **toutes** les fiches : nom, marques, groupe PNNS et son libellé
   français (``CATEGORY_LABELS``). Chaque mot-clé donné par le modèle (``mots`` de
   ``lister_produits``, sans article ni préposition) en mot entier, au singulier ou au pluriel : « biscuits » trouve « Biscuit nature » et les 461 « Biscuits and cakes » ; « chips » ne
   trouve ni « Archipel » ni « Chipolata », « eau » ne trouve pas « gâteau ». Un mot du nom peut être
   un ingrédient (« cabillaud pané aux céréales »). Les mots d'abord, parce qu'un filtre Nutri-Score
   fait chuter la similarité (biscuits notés A ou B : 0,48 au mieux). Les métadonnées des 5 316
   fiches (0,5 s à lire) sont gardées ``SHEETS_TTL_S`` secondes ;
2. sinon repli sémantique : ``LIST_CANDIDATES`` fiches, gardées à au moins ``NAME_THRESHOLD`` et à
   moins de ``LIST_MARGIN`` de la meilleure ;
3. filtre Nutri-Score sur les produits trouvés, jamais avant : sinon le repli sémantique remplaçait
   un type sans produit bien noté par un autre (jus de citron pour « jus d'orange » noté B) ;
4. tri sur une valeur pour 100 g ou sur le score Nutri-Score ; valeur non renseignée en dernier.
"""

from __future__ import annotations

import re
import time
from typing import Any, Callable

from ..catalog import code_variants, normalize_text, to_number, word_matches
from ..corpus.embeddings import embed_model, embed_model_id, embed_query
from ..corpus.sheets import UNKNOWN
from .search import Hit, query_collection
from .store import DOCUMENTS, SHEETS, chroma_client, open_collection

CANDIDATES = 20          # fiches examinées pour une recherche par nom
NAME_THRESHOLD = 0.5     # en dessous, une fiche n'est jamais retenue par le repli sémantique
NAME_MARGIN = 0.03       # repli sémantique : écart maximal avec la meilleure fiche
DOCUMENT_THRESHOLD = 0.5  # en dessous, un passage n'a pas de rapport avec la question
LIST_CANDIDATES = 50     # liste : fiches examinées par le repli sémantique
LIST_MARGIN = 0.05       # liste : écart maximal avec la meilleure fiche (repli sémantique)
SHEETS_TTL_S = 600       # métadonnées de toutes les fiches gardées en mémoire (suivent le pipeline)

# Champ des métadonnées d'une fiche -> colonne du catalogue (nutriscope.catalog.DETAIL_COLUMNS)
ROW_FIELDS = {
    "name": "name", "brands": "brands", "quantity": "quantity", "pnns_group_1": "pnns_group_1",
    "pnns_group_2": "pnns_group_2", "labels": "labels", "nutriscore_score": "nutriscore",
    "nutriscore": "nutriscore_grade", "nova_group": "nova_group",
    "energy_kcal_100g": "energy_kcal_100g", "fat_100g": "fat_100g", "saturated_fat_100g": "saturated_fat_100g",
    "sugars_100g": "sugars_100g", "salt_100g": "salt_100g", "fiber_100g": "fiber_100g",
    "proteins_100g": "proteins_100g", "energy_100g": "energy_100g", "carbohydrates_100g": "carbohydrates_100g",
    "fruits_vegetables_legumes_100g": "fruits_vegetables_legumes_100g",
}

Embedder = Callable[[str], list[float]]


def metadata_to_row(metadata: dict[str, Any]) -> dict[str, Any]:
    """Métadonnées d'une fiche -> ligne au format du catalogue SQL (absent ou « non renseigné » : None)."""
    row = {"code": metadata["code"]}
    for field, column in ROW_FIELDS.items():
        value = metadata.get(field)
        row[column] = None if value == UNKNOWN else value
    return row


def matches_all_words(words: list[str], metadata: dict[str, Any]) -> bool:
    haystack = f"{metadata.get('name') or ''} {metadata.get('brands') or metadata.get('brand') or ''}"
    return all(word_matches(word, haystack) for word in words)


# Groupes PNNS (en anglais dans Open Food Facts) -> mots français cherchés avec le nom : sans eux,
# « céréales du petit-déjeuner » ne trouvait que 1 des 87 « Breakfast cereals ». Choisis pour ne pas
# déborder : « céréales » vise le petit-déjeuner (pas les pâtes et le riz, groupe « Cereals »), les
# fruits à coque ne répondent pas à « fruits ».
CATEGORY_LABELS = {
    "Sweets": "confiseries bonbons", "Biscuits and cakes": "biscuits gâteaux",
    "One-dish meals": "plats préparés", "Processed meat": "charcuterie",
    "Dressings and sauces": "sauces condiments", "Cereals": "féculents pâtes riz semoule",
    "Cheese": "fromages", "Fish and seafood": "poissons crustacés", "Meat": "viandes",
    "Chocolate products": "chocolats", "Vegetables": "légumes", "Milk and yogurt": "lait yaourts",
    "Fats": "matières grasses beurre huiles", "Sweetened beverages": "boissons sucrées sodas",
    "Bread": "pains", "Appetizers": "apéritifs chips crackers", "Teas and herbal teas and coffees": "thés tisanes cafés",
    "Fruits": "fruits", "Dairy desserts": "desserts lactés crèmes", "Breakfast cereals": "céréales petit-déjeuner",
    "Fruit juices": "jus de fruits", "Nuts": "oléagineux noix amandes", "Ice cream": "glaces",
    "Pastries": "viennoiseries pâtisseries", "Legumes": "légumineuses légumes secs",
    "Pizza pies and quiches": "pizzas tartes quiches", "Dried fruits": "fruits secs",
    "Artificially sweetened beverages": "boissons édulcorées sodas light", "Sandwiches": "sandwichs",
    "Soups": "soupes", "Alcoholic beverages": "boissons alcoolisées alcools", "Potatoes": "pommes de terre",
    "Plant-based milk substitutes": "boissons végétales", "Waters and flavored waters": "eaux",
    "Unsweetened beverages": "boissons", "Eggs": "oeufs œufs", "Baby milks": "laits infantiles",
    "Offals": "abats", "Fruit nectars": "nectars jus de fruits",
    # groupes larges (pnns_group_1) : seulement ceux qui ne débordent pas
    "Beverages": "boissons", "Milk and dairy products": "produits laitiers",
    "Cereals and potatoes": "féculents", "Sugary snacks": "produits sucrés",
    "Salty snacks": "snacks salés apéritifs",
}

def word_pattern(word: str) -> re.Pattern:
    """Mot entier, au singulier ou au pluriel : « biscuits » -> biscuit, biscuits ; « gateaux » ->
    gateau, gateaux. Les mots de 4 lettres au plus gardent leur forme (« jus », « eau »)."""
    stem = word[:-1] if len(word) > 4 and word[-1] in "sx" else word
    return re.compile(rf"\b{re.escape(stem)}[sx]?\b")


def matches_category(patterns: list[re.Pattern], metadata: dict[str, Any]) -> bool:
    """Nom, marques, groupe PNNS fin (anglais et français) et libellé français du groupe large (son nom
    anglais est trop large : « Fruits and vegetables » répondrait à « fruits » pour tous les légumes)."""
    group, broad = metadata.get("pnns_group_2"), metadata.get("pnns_group_1")
    haystack = normalize_text(" ".join(str(part or "") for part in (
        metadata.get("name"), metadata.get("brands"), group, CATEGORY_LABELS.get(group), CATEGORY_LABELS.get(broad))))
    return all(pattern.search(haystack) for pattern in patterns)


def sort_key(field: str, descending: bool) -> Callable[[dict[str, Any]], tuple]:
    """Valeur non renseignée en dernier ; à égalité, le meilleur score Nutri-Score, puis le nom."""
    def key(metadata):
        value, score = to_number(metadata.get(field)), to_number(metadata.get("nutriscore_score"))
        return (value is None, -(value or 0) if descending else (value or 0),
                score is None, score or 0, normalize_text(metadata.get("name") or ""))
    return key


class RagIndex:
    """Fiches et documents de l'index Chroma, interrogés par les outils de l'assistant."""

    def __init__(self, client=None, embedder: Embedder | None = None):
        self._client = client
        self._embedder = embedder
        self._collections: dict[str, Any] = {}
        self._sheets: tuple[float, list[dict[str, Any]]] | None = None

    @classmethod
    def from_env(cls) -> "RagIndex":
        return cls()

    # ------------------------------------------------------------------ accès paresseux

    def collection(self, name: str):
        """Ouverte au premier appel : construire l'assistant ne demande ni Chroma ni Ollama."""
        if name not in self._collections:
            self._client = self._client or chroma_client()
            self._collections[name] = open_collection(self._client, name, embed_model_id(), create=False)
        return self._collections[name]

    def embed(self, text: str) -> list[float]:
        return self._embedder(text) if self._embedder else embed_query(text, model=embed_model())

    def all_sheets(self) -> list[dict[str, Any]]:
        """Métadonnées de toutes les fiches, relues après ``SHEETS_TTL_S`` secondes."""
        if self._sheets is None or time.monotonic() - self._sheets[0] > SHEETS_TTL_S:
            self._sheets = (time.monotonic(), self.collection(SHEETS).get(include=["metadatas"])["metadatas"])
        return self._sheets[1]

    # ------------------------------------------------------------------ interface Catalog

    def find_by_code(self, code: str) -> list[dict[str, Any]]:
        """Fiche dont le code-barres est ``code`` (variantes UPC-A / EAN-13 comprises)."""
        found = self.collection(SHEETS).get(ids=[f"fiche:{variant}" for variant in code_variants(code)],
                                            include=["metadatas"])
        return [metadata_to_row(metadata) for metadata in found["metadatas"]]

    def search_by_name(self, words: list[str], limit: int, query: str | None = None) -> tuple[int, list[dict]]:
        """(nombre de fiches retenues, ``limit`` premières lignes) ; ``query`` : le nom tel qu'écrit
        (accents compris), à défaut les mots normalisés."""
        hits = query_collection(self.collection(SHEETS), SHEETS, self.embed(query or " ".join(words)),
                                CANDIDATES, None)
        kept = [hit for hit in hits if matches_all_words(words, hit.metadata)]
        if kept:
            full = " ".join(words)   # nom exact d'abord, comme la recherche SQL ; sinon l'ordre de proximité
            kept.sort(key=lambda hit: normalize_text(hit.metadata.get("name") or "") != full)
        else:
            above = [hit for hit in hits if hit.score >= NAME_THRESHOLD]
            kept = [hit for hit in above if hit.score >= above[0].score - NAME_MARGIN] if above else []
        return len(kept), [metadata_to_row(hit.metadata) for hit in kept[:limit]]

    # ------------------------------------------------------------------ listes

    def list_products(self, words: list[str], query: str, grades: list[str] | None, sort: str,
                      descending: bool, limit: int) -> tuple[int, list[dict[str, Any]]]:
        """(nombre de fiches retenues, ``limit`` premières lignes triées sur ``sort``) : les produits du
        type (mots, sinon repli sémantique), **puis** le filtre ``grades`` (lettres Nutri-Score permises).
        Dans cet ordre : aucun jus d'orange noté A ou B, c'est ``introuvable``, pas les jus de citron que
        le repli sémantique trouvait sous le filtre (mesuré)."""
        patterns = [word_pattern(word) for word in words]
        found = [metadata for metadata in self.all_sheets() if matches_category(patterns, metadata)]
        if not found:
            hits = query_collection(self.collection(SHEETS), SHEETS, self.embed(query), LIST_CANDIDATES, None)
            above = [hit for hit in hits if hit.score >= NAME_THRESHOLD]
            found = [hit.metadata for hit in above if hit.score >= above[0].score - LIST_MARGIN] if above else []
        kept = [metadata for metadata in found if grades is None or metadata.get("nutriscore") in grades]
        kept.sort(key=sort_key(sort, descending))
        return len(kept), [metadata_to_row(metadata) for metadata in kept[:limit]]

    # ------------------------------------------------------------------ aiguillage

    def closest_collection(self, question: str) -> str:
        """``documents`` si un passage est plus proche de la question que toute fiche (et au-dessus de
        ``DOCUMENT_THRESHOLD``), sinon ``sheets``. Mesuré le 18/11/2026 sur 14 questions : écart
        documents - fiches de +0,15 à +0,27 pour les questions générales couvertes par les documents,
        de -0,02 à -0,27 pour les questions produit."""
        vector = self.embed(question)
        best = {}
        for name in (SHEETS, DOCUMENTS):
            hits = query_collection(self.collection(name), name, vector, 1, None)
            best[name] = hits[0].score if hits else -1.0
        if best[DOCUMENTS] >= DOCUMENT_THRESHOLD and best[DOCUMENTS] > best[SHEETS]:
            return DOCUMENTS
        return SHEETS

    # ------------------------------------------------------------------ documents

    def search_documents(self, question: str, limit: int) -> list[Hit]:
        """Passages des documents de référence à au moins ``DOCUMENT_THRESHOLD`` de la question."""
        hits = query_collection(self.collection(DOCUMENTS), DOCUMENTS, self.embed(question), limit, None)
        return [hit for hit in hits if hit.score >= DOCUMENT_THRESHOLD]
