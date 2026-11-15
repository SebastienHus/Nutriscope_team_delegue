"""
Du texte brut du modèle à une lecture d'étiquette validée.

1. ``extract_json`` : le premier objet JSON de la réponse (sans ``eval``) ;
2. ``RawReading`` (Pydantic) : la forme demandée dans le prompt ; les clés en trop sont ignorées ;
3. ``parse_printed`` : chaque nutriment est demandé **tel qu'imprimé** (« 1,1 g », « < 0,5 g »,
   « 2255 kJ / 539 kcal ») et le nombre est extrait par le code. Un 0 nu, qui n'a pas été recopié
   depuis un texte imprimé, est écarté : c'est le garde-fou en code contre les zéros inventés ;
4. ``check_reading`` : plausibilité et cohérence interne de l'étiquette.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from .ean import clean_barcode

NUTRIENTS = ("kj", "kcal", "lipides", "satures", "glucides", "sucres", "fibres", "proteines", "sel")
MAX_VALUE = {"kj": 3800.0, "kcal": 900.0}          # pour 100 g ; 100 g pour les autres nutriments
KJ_PER_KCAL = 4.184
TOLERANCE = 0.5                                     # g, pour les contrôles "partie <= tout"

_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
_LESS_THAN = re.compile(r"(<|≤|inf[ée]rieur|moins de|less than)", re.IGNORECASE)
_TRACES = re.compile(r"\btraces?\b", re.IGNORECASE)


def extract_json(text: str) -> dict[str, Any] | None:
    """Premier objet JSON trouvé dans le texte du modèle (blocs de code et commentaires autour ignorés)."""
    if not text:
        return None
    decoder = json.JSONDecoder()
    for start in (index for index, char in enumerate(text) if char == "{"):
        try:
            value, _ = decoder.raw_decode(text[start:])
        except ValueError:
            continue
        if isinstance(value, dict):
            return value
    return None


class RawReading(BaseModel):
    """Ce que demande le prompt. Chaque champ est facultatif : un champ absent est inconnu."""

    model_config = ConfigDict(extra="ignore")

    tableau_visible: bool | None = None
    nom: str | None = None
    marque: str | None = None
    code_barres: str | None = None
    base: str | None = None
    nutriments: dict[str, Any] = {}
    ingredients: list[str] | None = None

    @field_validator("nom", "marque", "code_barres", "base", mode="before")
    @classmethod
    def _text(cls, value: Any) -> str | None:
        if value is None or isinstance(value, (dict, list)):
            return None
        value = str(value).strip()
        return value if value and value.lower() not in {"null", "none", "n/a", "inconnu"} else None

    @field_validator("nutriments", mode="before")
    @classmethod
    def _nutrients(cls, value: Any) -> dict[str, Any]:
        return value if isinstance(value, dict) else {}

    @field_validator("ingredients", mode="before")
    @classmethod
    def _ingredients(cls, value: Any) -> list[str] | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = [part for part in re.split(r",(?![^()]*\))", value)]
        if not isinstance(value, list):
            return None
        items = [str(item).strip() for item in value if isinstance(item, (str, int, float)) and str(item).strip()]
        return items or None


def parse_printed(text: Any, key: str) -> tuple[float | None, bool]:
    """(valeur, "inférieur à") depuis un texte imprimé. Illisible, absent ou "traces" -> (None, False)."""
    if text is None or isinstance(text, bool):
        return None, False
    if isinstance(text, (int, float)):
        # Un nombre nu n'a pas été recopié depuis un texte imprimé. Gardé, sauf 0 : un 0 nu est la
        # valeur typique qu'invente un modèle pour une ligne absente de l'étiquette.
        return (float(text), False) if text > 0 else (None, False)
    text = str(text).strip()
    if not text or _TRACES.search(text):
        return None, False
    if key in ("kj", "kcal"):                    # "2255 kJ / 539 kcal" : prendre le nombre placé avant l'unité
        unit = "kj" if key == "kj" else "kcal"
        match = re.search(rf"(\d+(?:[.,]\d+)?)\s*{unit}", text, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(",", ".")), bool(_LESS_THAN.search(text[:match.start()]))
        if re.search(r"k\s*j|kcal|cal", text, re.IGNORECASE):   # seulement l'autre unité : pas cette valeur
            return None, False
    match = _NUMBER.search(text)
    if not match:
        return None, False
    return float(match.group(0).replace(",", ".")), bool(_LESS_THAN.search(text[:match.start()]))


def normalize_base(text: str | None) -> str | None:
    if not text:
        return None
    compact = text.lower().replace(" ", "")
    if "100ml" in compact:
        return "100 ml"
    if "100g" in compact:
        return "100 g"
    return None


@dataclass
class Reading:
    """Une lecture validée d'une étiquette (clés du contrat)."""

    nom: str | None = None
    marque: str | None = None
    code_barres: str | None = None
    base: str | None = None
    nutriments: dict[str, float | None] = field(default_factory=lambda: dict.fromkeys(NUTRIENTS))
    inferieur_a: list[str] = field(default_factory=list)
    ingredients: list[str] | None = None
    table_visible: bool = False
    alerts: list[str] = field(default_factory=list)

    @property
    def has_values(self) -> bool:
        return any(value is not None for value in self.nutriments.values())


def to_reading(data: dict[str, Any] | None) -> tuple[Reading | None, list[str]]:
    """JSON brut -> Reading. (None, [problème]) quand le JSON n'a pas la forme attendue."""
    if data is None:
        return None, ["la réponse du modèle ne contient pas d'objet JSON"]
    try:
        raw = RawReading.model_validate(data)
    except ValidationError as exc:
        return None, [f"JSON hors schéma : {exc.errors()[0]['loc']} {exc.errors()[0]['msg']}"]

    reading = Reading(nom=raw.nom, marque=raw.marque, code_barres=clean_barcode(raw.code_barres),
                      base=normalize_base(raw.base), ingredients=raw.ingredients)
    for key in NUTRIENTS:
        printed = raw.nutriments.get(key)
        value, less_than = parse_printed(printed, key)
        if value is None and isinstance(printed, (int, float)) and not isinstance(printed, bool):
            reading.alerts.append(f"{key} : 0 rendu sans texte imprimé, valeur écartée (null)")
        reading.nutriments[key] = value
        if value is not None and less_than:
            reading.inferieur_a.append(key)
    if raw.code_barres and not reading.code_barres:
        reading.alerts.append("code-barres lu mais pas uniquement des chiffres : ignoré")

    reading.table_visible = raw.tableau_visible is not False
    if not reading.table_visible and reading.has_values:
        reading.alerts.append("le modèle dit ne voir aucun tableau mais rend des valeurs : valeurs écartées")
        reading.nutriments = dict.fromkeys(NUTRIENTS)
        reading.inferieur_a = []
    if reading.has_values and reading.base is None:
        reading.alerts.append("base (100 g ou 100 ml) non lue")
    return reading, []


def check_reading(reading: Reading) -> list[tuple[str, tuple[str, ...]]]:
    """Problèmes de plausibilité : [(message, champs en cause)]. Liste vide = étiquette cohérente."""
    n = reading.nutriments
    problems: list[tuple[str, tuple[str, ...]]] = []
    for key, value in n.items():
        if value is not None and not 0 <= value <= MAX_VALUE.get(key, 100.0):
            problems.append((f"{key} = {value} hors bornes pour 100 g", (key,)))
    if n["satures"] is not None and n["lipides"] is not None and n["satures"] > n["lipides"] + TOLERANCE:
        problems.append((f"saturés ({n['satures']}) > lipides ({n['lipides']})", ("satures",)))
    if n["sucres"] is not None and n["glucides"] is not None and n["sucres"] > n["glucides"] + TOLERANCE:
        problems.append((f"sucres ({n['sucres']}) > glucides ({n['glucides']})", ("sucres",)))
    if n["kj"] is not None and n["kcal"] is not None:
        expected = n["kcal"] * KJ_PER_KCAL
        if abs(n["kj"] - expected) > 0.06 * max(expected, n["kj"]) + 5:
            problems.append((f"kJ ({n['kj']}) et kcal ({n['kcal']}) incohérents", ("kj", "kcal")))
    masses = [n[k] for k in ("lipides", "glucides", "proteines", "fibres", "sel") if n[k] is not None]
    if reading.base == "100 g" and sum(masses) > 105:
        problems.append((f"somme des nutriments ({sum(masses):.1f} g) > 100 g", ()))
    if n["kcal"] is not None and all(n[k] is not None for k in ("lipides", "glucides", "proteines")):
        computed = 9 * n["lipides"] + 4 * n["glucides"] + 4 * n["proteines"] + 2 * (n["fibres"] or 0)
        if abs(computed - n["kcal"]) > 0.25 * max(computed, n["kcal"]) + 15:
            problems.append((f"énergie ({n['kcal']} kcal) incohérente avec les macronutriments "
                             f"(≈ {computed:.0f} kcal)", ()))
    return problems


def discard_fields(reading: Reading, problems: list[tuple[str, tuple[str, ...]]]) -> None:
    """Dernier recours après les relances : les champs en cause passent à null, avec une alerte."""
    for message, fields in problems:
        for key in fields:
            reading.nutriments[key] = None
            if key in reading.inferieur_a:
                reading.inferieur_a.remove(key)
        reading.alerts.append(f"contrôle échoué : {message}" + (" ; valeur écartée" if fields else ""))
