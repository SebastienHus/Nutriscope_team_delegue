"""
Étape 4 du workflow : combiner plusieurs lectures champ par champ.

Pour chaque champ, la valeur donnée par une majorité stricte des lectures l'emporte. Sans
majorité, le champ vaut null et une alerte le nomme. Règle d'égalité : les nombres sont comparés
arrondis à deux décimales (1.1 == 1.10) ; les textes sans tenir compte de la casse ni des accents.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from ..catalog import normalize_text
from .validation import NUTRIENTS, Reading


def _key(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, str):
        return " ".join(normalize_text(value).split())
    if isinstance(value, list):
        return tuple(_key(item) for item in value)
    return value


def majority(values: list[Any]) -> tuple[Any, bool]:
    """(valeur de la majorité stricte, True) ou (None, False). Une seule valeur : elle-même."""
    if len(values) == 1:
        return values[0], True
    counts = Counter(_key(value) for value in values)
    key, count = counts.most_common(1)[0]
    if count * 2 <= len(values):
        return None, False
    return next(value for value in values if _key(value) == key), True


def vote(readings: list[Reading]) -> Reading:
    """Consensus champ par champ des lectures (les lectures elles-mêmes ne sont pas modifiées)."""
    if len(readings) == 1:
        return readings[0]
    result = Reading(table_visible=majority([r.table_visible for r in readings])[0] or False)
    for name in ("nom", "marque", "code_barres", "base", "ingredients"):
        value, agreed = majority([getattr(r, name) for r in readings])
        setattr(result, name, value)
        if not agreed:
            result.alerts.append(f"désaccord entre lectures sur {name}")
    for key in NUTRIENTS:
        value, agreed = majority([r.nutriments[key] for r in readings])
        result.nutriments[key] = value
        if not agreed:
            result.alerts.append(f"désaccord entre lectures sur {key} : "
                                 f"{[r.nutriments[key] for r in readings]} -> null")
        elif value is not None:
            # "< 0,5" gardé quand la plupart des lectures qui donnent cette valeur ont vu le "<"
            agreeing = [r for r in readings if _key(r.nutriments[key]) == _key(value)]
            if sum(key in r.inferieur_a for r in agreeing) * 2 > len(agreeing):
                result.inferieur_a.append(key)
    for reading in readings:
        result.alerts += [alert for alert in reading.alerts if alert not in result.alerts]
    return result
