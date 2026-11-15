"""
Étape 3 du workflow : retrouver le produit dans le catalogue avec ``chercher_produit``, puis comparer.

- un code-barres est lu et sa clé de contrôle est valide -> recherche par code ;
- sinon (ou s'il est introuvable) un nom est lu -> recherche par nom. Une recherche par nom n'est
  acceptée que si elle donne un seul produit dont la marque correspond à la marque lue (quand les
  deux sont connues), ou un seul produit parmi les ambigus une fois filtrés sur la marque ;
- tout le reste reste non vérifié : mieux vaut un vrai « non vérifié » qu'un faux « vérifié ».
"""

from __future__ import annotations

from typing import Any, Callable

from ..catalog import normalize_text, search_words
from .ean import is_valid_barcode
from .validation import NUTRIENTS, Reading

SearchTool = Callable[[dict[str, Any]], dict[str, Any]]


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

    if reading.nom and search_words(reading.nom):
        result = search({"nom": reading.nom[:120], "limite": 5})
        if "erreur" in result:
            alerts.append(f"recherche par nom impossible : {result['erreur']}")
            return None, alerts
        candidates = [p for p in result.get("produits", []) if _brand_matches(reading.marque, p.get("marque"))]
        complete = result.get("total", 0) <= len(result.get("produits", []))
        if len(candidates) == 1 and complete:
            if result["statut"] == "ambigu":
                alerts.append(f"nom ambigu ({result['total']} fiches), départagé par la marque")
            return candidates[0], alerts
        if result.get("statut") == "introuvable":
            alerts.append(f"« {reading.nom} » absent du catalogue")
        else:
            alerts.append(f"produit ambigu : « {reading.nom} » correspond à {result.get('total')} fiches")
    elif not code:
        alerts.append("ni code-barres ni nom lus : produit non identifié")
    return None, alerts


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
