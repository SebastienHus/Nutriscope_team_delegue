"""
Étape 3 du workflow : retrouver le produit dans le catalogue avec ``chercher_produit``, puis comparer.

- un code-barres est lu et sa clé de contrôle est valide -> recherche par code ;
- sinon (ou s'il est introuvable) un nom ou une marque est lu -> recherche par nom : d'abord le nom
  avec la marque (« PRINCE LU »), puis le nom seul ; la marque seule quand aucun nom n'est lu
  (« Nutella » rangé en marque). Une fiche est acceptée :
  - si elle est la seule trouvée dont la marque correspond à la marque lue ;
  - ou, sinon, si elle est la seule dont les valeurs nutritionnelles concordent avec celles de
    l'étiquette (au moins ``MIN_SHARED_VALUES`` valeurs comparées, toutes dans la tolérance de
    ``same_value``). Dans les deux cas, la recherche doit avoir rendu **toutes** les fiches trouvées :
    une seule fiche concordante parmi les 5 premières de « PRINCE » (12 fiches) n'est pas une seule
    parmi toutes ; mesuré le 15/11, 8 « verifie » sur 12 désignaient alors un autre format ou un autre
    pays du produit. La fiche aux mêmes valeurs est seulement citée dans l'alerte ;
- tout le reste reste non vérifié : mieux vaut un vrai « non vérifié » qu'un faux « vérifié ».
"""

from __future__ import annotations

from typing import Any, Callable

from ..catalog import normalize_text, search_words
from .ean import is_valid_barcode
from .validation import NUTRIENTS, Reading

SearchTool = Callable[[dict[str, Any]], dict[str, Any]]
SEARCH_LIMIT = 5                 # le maximum de chercher_produit
MIN_SHARED_VALUES = 4            # valeurs comparées au minimum pour départager des fiches par les valeurs


def _brand_matches(read: str | None, sheet: str | None) -> bool:
    if not read or not sheet:
        return True                      # rien à contredire
    read_words, sheet_words = set(search_words(read)), set(search_words(sheet.replace("-", " ")))
    return bool(read_words & sheet_words) or normalize_text(read).replace(" ", "-") in normalize_text(sheet)


def find_sheet(reading: Reading, search: SearchTool) -> tuple[dict[str, Any] | None, list[str]]:
    """(fiche du produit, alertes). La fiche vaut None quand le produit n'est pas retrouvé avec certitude."""
    alerts: list[str] = []
    code = reading.code_barres
    if code:
        if not is_valid_barcode(code):
            alerts.append(f"code-barres {code} mal lu (clé de contrôle fausse) : non utilisé")
        else:
            result = search({"code": code, "limite": 1})
            if result.get("statut") == "ok":
                return result["produits"][0], alerts
            alerts.append(f"code-barres {code} absent du catalogue" if "erreur" not in result
                          else f"recherche par code impossible : {result['erreur']}")

    queries = name_queries(reading)
    if not queries:
        if not code:
            alerts.append("ni code-barres ni nom lus : produit non identifié")
        return None, alerts
    last = ""
    for query in queries:
        result = search({"nom": query[:120], "limite": SEARCH_LIMIT})
        if "erreur" in result:
            last = f"recherche « {query} » impossible : {result['erreur']}"
            continue
        if result.get("statut") == "introuvable":
            last = f"« {query} » absent du catalogue"
            continue
        products, total = result.get("produits", []), result.get("total", 0)
        candidates = [p for p in products if _brand_matches(reading.marque, p.get("marque"))]
        if len(candidates) == 1 and total <= len(products):
            if result["statut"] == "ambigu":
                alerts.append(f"nom ambigu ({total} fiches), départagé par la marque")
            return candidates[0], alerts
        agreeing = [p for p in candidates if values_agree(reading, p)]
        complete = total <= len(products)
        if len(agreeing) == 1 and complete:
            alerts.append(f"« {query} » : {total} fiches, départagé par les valeurs de l'étiquette")
            return agreeing[0], alerts
        last = f"produit ambigu : « {query} » correspond à {total} fiches"
        if agreeing:
            seen = "" if complete else f" parmi les {len(products)} premières"
            last += (f" ; mêmes valeurs que {', '.join(str(p.get('code')) for p in agreeing)}{seen} :"
                     f" produit non identifié avec certitude")
    alerts.append(last)
    return None, alerts


def name_queries(reading: Reading) -> list[str]:
    """Recherches par nom, de la plus précise à la plus large : nom + marque, nom seul ; marque seule sans nom."""
    name = reading.nom if reading.nom and search_words(reading.nom) else None
    brand = reading.marque if reading.marque and search_words(reading.marque) else None
    queries = []
    if name and brand and not set(search_words(brand)) <= set(search_words(name)):
        queries.append(f"{name} {brand}")
    if name:
        queries.append(name)
    elif brand:
        queries.append(brand)
    return queries


def values_agree(reading: Reading, sheet: dict[str, Any]) -> bool:
    """La fiche a les valeurs de l'étiquette : assez de valeurs comparables, et aucun écart."""
    catalog = sheet_values(sheet)
    shared = [key for key in NUTRIENTS if reading.nutriments.get(key) is not None and catalog.get(key) is not None]
    return len(shared) >= MIN_SHARED_VALUES and not differences(reading, sheet)


def sheet_values(sheet: dict[str, Any]) -> dict[str, float | None]:
    """Les 9 nutriments du contrat du scanner, pris dans une fiche du catalogue."""
    values = {**(sheet.get("nutriments") or {}), **(sheet.get("nutriments_complementaires") or {})}
    return {key: values.get(key) for key in NUTRIENTS}


def same_value(label: float, catalog: float, key: str) -> bool:
    if key in ("kj", "kcal"):
        return abs(label - catalog) <= max(2.0, 0.03 * max(label, catalog))
    return abs(label - catalog) <= max(0.15, 0.06 * max(label, catalog))


def differences(reading: Reading, sheet: dict[str, Any]) -> list[dict[str, Any]]:
    """Nutriments lus sur l'étiquette et présents dans la fiche, dont les valeurs ne concordent pas."""
    catalog = sheet_values(sheet)
    gaps = []
    for key in NUTRIENTS:
        label, known = reading.nutriments.get(key), catalog.get(key)
        if label is None or known is None:
            continue
        if key in reading.inferieur_a and known <= label:     # "< 0,5 g" contre 0,3 g : pas de contradiction
            continue
        if not same_value(label, known, key):
            gaps.append({"champ": key, "etiquette": label, "catalogue": known})
    return gaps
