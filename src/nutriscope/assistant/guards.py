"""
Garde-fous écrits en code (ils tiennent quoi que fasse le modèle).

- ``medical_refusal`` : une question de santé (pathologie, traitement, grossesse, régime
  thérapeutique) est refusée **avant** tout appel au modèle. Une règle en code ne se négocie pas,
  ne coûte rien et se teste ; les demandes hors sujet, trop variées pour une liste de mots, sont
  laissées au prompt système (seconde couche).
- ``unsupported_numbers`` : chaque nombre d'une réponse doit venir des faits (résultats d'outil,
  résultat du scanner, question de l'utilisateur). Utilisé par la relecture de l'assistant et du scanner.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterable

from ..catalog import normalize_text

# Cherchés dans la question normalisée (minuscules, sans accents)
MEDICAL_PATTERNS = [
    r"\bdiabet", r"\bmedicament", r"\btraitement", r"\bpatholog", r"\bmaladie", r"\bje suis malade",
    r"\bcholesterol", r"\bhypertension", r"\btension arterielle", r"\binsuffisan\w* (renale|cardiaque|hepatique)",
    r"\benceinte\b", r"\bgrossesse", r"\ballait", r"\bcancer", r"\binsuline", r"\bglycemi", r"\bordonnance",
    r"\bmedecin\b", r"\bchimio", r"\bregime (therapeutique|medical)", r"\bcoeliaqu", r"\bceliaqu",
    r"\bcrohn", r"\bdialys", r"\banorexi", r"\bboulimi", r"\bsymptome", r"\bposologie",
]
_MEDICAL = re.compile("|".join(MEDICAL_PATTERNS))

MEDICAL_REFUSAL = (
    "Je ne peux pas donner de conseil médical : pour une pathologie, un traitement ou un régime adapté à "
    "votre santé, rapprochez-vous de votre médecin ou d'un diététicien. Je peux en revanche vous indiquer le "
    "Nutri-Score et les valeurs nutritionnelles d'un produit du catalogue."
)


def medical_refusal(question: str) -> str | None:
    """Le message de refus si la question est médicale, sinon None."""
    return MEDICAL_REFUSAL if _MEDICAL.search(normalize_text(question)) else None


# ----------------------------------------------------------------------------
# Nombres d'une réponse
# ----------------------------------------------------------------------------

# Un nombre, avec une partie décimale facultative ("1,1" ou "1.1"), qui n'est pas dans un mot ni un nombre plus long
_NUMBER = re.compile(r"(?<![\w.,])(\d+(?:[.,]\d+)?)(?![\w]|[.,]\d)")
_UNIT = re.compile(r"\s*(g|mg|kg|kcal|kj|%|ml|cl|l|gramme|grammes|calories?)\b", re.IGNORECASE)
ALWAYS_ALLOWED = {100.0}          # "pour 100 g"
SMALL_COUNT = 10                  # "2 produits", "3 fiches" : des comptes, sans unité


def _facts_numbers(facts: Iterable[Any]) -> set[float]:
    numbers: set[float] = set()

    def walk(value: Any) -> None:
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            numbers.add(float(value))
        elif isinstance(value, str):
            numbers.update(float(n.replace(",", ".")) for n in _NUMBER.findall(value))
        elif isinstance(value, dict):
            for item in value.values():
                walk(item)
        elif isinstance(value, (list, tuple, set)):
            for item in value:
                walk(item)

    for fact in facts:
        if isinstance(fact, str):
            try:
                fact = json.loads(fact)
            except ValueError:
                pass
        walk(fact)
    return numbers


def _matches(written: str, value: float, fact: float) -> bool:
    """Même valeur, aux arrondis d'affichage près (56,8 écrit 57, 0,456 écrit 0,46)."""
    if abs(value - fact) <= 1e-6:
        return True
    decimals = len(written.replace(",", ".").partition(".")[2])
    return round(fact, decimals) == value


def unsupported_numbers(answer: str, facts: Iterable[Any]) -> list[str]:
    """Nombres de ``answer`` absents de tous les faits (liste vide = chaque nombre est justifié)."""
    known = _facts_numbers(facts) | ALWAYS_ALLOWED
    unsupported = []
    for match in _NUMBER.finditer(answer):
        written = match.group(1)
        value = float(written.replace(",", "."))
        has_unit = bool(_UNIT.match(answer, match.end()))
        if not has_unit and value.is_integer() and value <= SMALL_COUNT:
            continue
        if not any(_matches(written, value, fact) for fact in known):
            unsupported.append(written)
    return unsupported


def mentions_unverified(answer: str) -> bool:
    return "non verifi" in normalize_text(answer)


def numbers_in(text: str) -> list[str]:
    """Nombres d'un texte, tels qu'écrits ("56,3", "539")."""
    return _NUMBER.findall(text)


def where_found(written: str, facts: Iterable[Any], path: str = "") -> list[str]:
    """Chemins JSON des faits qui contiennent le nombre ``written`` (pour montrer d'où vient un chiffre)."""
    value = float(written.replace(",", "."))
    found: list[str] = []

    def walk(item: Any, here: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                walk(child, f"{here}.{key}" if here else str(key))
        elif isinstance(item, (list, tuple)):
            for index, child in enumerate(item):
                walk(child, f"{here}[{index}]")
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            if _matches(written, value, float(item)):
                found.append(here)
        elif isinstance(item, str) and any(_matches(written, value, float(n.replace(",", ".")))
                                           for n in _NUMBER.findall(item)):
            found.append(here)

    for index, fact in enumerate(facts):
        walk(fact, f"{path}[{index}]")
    return found
