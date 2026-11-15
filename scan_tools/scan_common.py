"""Outils de test de l'atelier « scanner d'étiquettes » : ce que partagent la mesure et les tests.

Ce fichier ne contient aucune partie du scanner. Il sait seulement :

- retrouver votre fonction ``scan_label`` (option ``--scanner``) ;
- lire la vérité terrain du lot (``data/verite_terrain.csv``) ;
- vérifier la forme du résultat (le contrat du README).

Les clés du résultat (``statut``, ``nutriments``, ``lipides``…) sont celles du contrat : elles restent
telles quelles. Vous n'avez pas à modifier ce fichier.
"""

from __future__ import annotations

import csv
import importlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Callable

# Où chercher la fonction si on ne précise rien : src/scanner.py, fonction scan_label.
DEFAULT_SCANNER = "src/scanner.py:scan_label"

# Dossier data/ placé à côté du dossier scan_tools/.
DATA = Path(__file__).resolve().parent.parent / "data"

NUTRIENTS = ("kj", "kcal", "lipides", "satures", "glucides", "sucres", "fibres", "proteines", "sel")
STATUSES = ("verifie", "non_verifie", "illisible")
BASES = ("100 g", "100 ml", None)
METRICS = ("appels_modele", "latence_s", "tokens_entree", "tokens_sortie")


class ScannerNotFound(Exception):
    """La fonction indiquée par --scanner n'a pas pu être chargée."""


def load_scanner(target: str = DEFAULT_SCANNER) -> Callable[[Any], dict[str, Any]]:
    """Charge ``fichier.py:fonction`` (ou ``paquet.module:fonction``), depuis le dossier courant."""
    if ":" not in target:
        raise ScannerNotFound(f"« {target} » : écrivez fichier.py:nom_fonction, par exemple {DEFAULT_SCANNER}")
    path, function_name = target.rsplit(":", 1)
    file = Path(path if path.endswith(".py") else path.replace(".", "/") + ".py")
    file = (Path.cwd() / file).resolve() if not file.is_absolute() else file
    # Le dossier courant (import « from src.x import … ») et le dossier du fichier
    # (import d'un module voisin, « from controles import … ») sont tous deux cherchés.
    if not file.is_file():
        raise ScannerNotFound(
            f"fichier introuvable : {path} (cherché depuis {Path.cwd()}).\n"
            f"Lancez la commande depuis la racine de votre dépôt, ou indiquez où est votre fonction :\n"
            f"  --scanner chemin/vers/fichier.py:scan_label")
    for folder in (file.parent, Path.cwd()):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    try:
        relative = file.relative_to(Path.cwd().resolve()).with_suffix("")
    except ValueError:
        relative = None
    try:
        if relative is not None and all(p.isidentifier() for p in relative.parts):
            # Import par nom de module : les imports relatifs (« from .controles import … ») marchent.
            module = importlib.import_module(".".join(relative.parts))
        else:
            spec = importlib.util.spec_from_file_location(file.stem, file)
            module = importlib.util.module_from_spec(spec)
            sys.modules[file.stem] = module
            spec.loader.exec_module(module)
    except Exception as e:
        raise ScannerNotFound(f"{path} existe, mais son import échoue : {type(e).__name__}: {e}") from None
    function = getattr(module, function_name, None)
    if not callable(function):
        raise ScannerNotFound(f"{path} ne définit pas de fonction {function_name}(image)")
    return function


def load_ground_truth(path: Path = DATA / "verite_terrain.csv") -> list[dict[str, Any]]:
    """Les 22 produits du lot. Une case vide = valeur absente de l'étiquette (None)."""
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["nutriments"] = {k: float(row[k]) if row[k] else None for k in NUTRIENTS}
        row["inferieur_a"] = [k for k in row["inferieur_a"].split(";") if k]
        row["base"] = row["base"] or None
    return rows


def photo(product: dict[str, Any], side: str = "etiquette") -> Path:
    return DATA / "photos" / f"{product['id']}_{product['code']}_{side}.jpg"


def is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


# --- Le contrat, règle par règle. Chaque règle rend la liste de ses problèmes (vide si tout va bien). ---

def _keys(r: dict, keys: tuple) -> list[str]:
    missing = [k for k in keys if k not in r]
    return [f"clé manquante : {k}" for k in missing]


def rule_dictionary(r: Any) -> list[str]:
    if not isinstance(r, dict):
        return [f"le scanner doit rendre un dictionnaire, il a rendu : {type(r).__name__}"]
    return _keys(r, ("statut", "produit", "base", "nutriments", "inferieur_a", "ingredients",
                     "fiche_catalogue", "ecarts", "alertes", "mesures"))


def rule_status(r: dict) -> list[str]:
    if r.get("statut") not in STATUSES:
        return [f"statut = {r.get('statut')!r} ; valeurs permises : {', '.join(STATUSES)}"]
    return []


def rule_product(r: dict) -> list[str]:
    p = r.get("produit")
    if not isinstance(p, dict):
        return ["produit doit être un dictionnaire {nom, marque, code_barres}"]
    problems = _keys(p, ("nom", "marque", "code_barres"))
    problems += [f"produit.{k} doit être un texte ou null, pas {type(p[k]).__name__}"
                 for k in ("nom", "marque", "code_barres") if k in p and p[k] is not None and not isinstance(p[k], str)]
    return problems


def rule_base(r: dict) -> list[str]:
    if r.get("base") not in BASES:
        return [f"base = {r.get('base')!r} ; valeurs permises : \"100 g\", \"100 ml\" ou null"]
    return []


def rule_nutrients(r: dict) -> list[str]:
    n = r.get("nutriments")
    if not isinstance(n, dict):
        return ["nutriments doit être un dictionnaire"]
    problems = [f"nutriment manquant : {k}" for k in NUTRIENTS if k not in n]
    problems += [f"nutriment en trop : {k} (les 9 clés du contrat, pas d'autres)" for k in n if k not in NUTRIENTS]
    for k, v in n.items():
        if v is not None and not is_number(v):
            problems.append(f"nutriments.{k} = {v!r} : un nombre (point décimal) ou null, pas un texte")
        elif v is not None and v < 0:
            problems.append(f"nutriments.{k} = {v} : une valeur négative est impossible")
    return problems


def rule_less_than(r: dict) -> list[str]:
    less_than, n = r.get("inferieur_a"), r.get("nutriments") or {}
    if not isinstance(less_than, list):
        return ["inferieur_a doit être une liste (vide s'il n'y a aucun « < »)"]
    return [f"inferieur_a contient {k!r} : il faut une clé de nutriment dont la valeur n'est pas null"
            for k in less_than if k not in NUTRIENTS or n.get(k) is None]


def rule_ingredients(r: dict) -> list[str]:
    ingredients = r.get("ingredients")
    if ingredients is None or (isinstance(ingredients, list) and all(isinstance(i, str) for i in ingredients)):
        return []
    return ["ingredients doit être une liste de textes, ou null"]


def rule_status_and_sheet(r: dict) -> list[str]:
    status, sheet, gaps = r.get("statut"), r.get("fiche_catalogue"), r.get("ecarts")
    problems = []
    if status == "verifie" and sheet is None:
        problems.append("statut verifie mais fiche_catalogue est null")
    if status != "verifie" and sheet is not None:
        problems.append(f"statut {status} mais fiche_catalogue est remplie : seul « verifie » a une fiche")
    if status != "verifie" and gaps:
        problems.append(f"statut {status} mais ecarts n'est pas vide : sans fiche, pas d'écart")
    return problems


def rule_unreadable(r: dict) -> list[str]:
    if r.get("statut") != "illisible":
        return []
    problems = []
    if any(v is not None for v in (r.get("nutriments") or {}).values()):
        problems.append("statut illisible mais des nutriments sont lus : ce serait non_verifie")
    if any(v is not None for v in (r.get("produit") or {}).values()):
        problems.append("statut illisible mais le produit est identifié : ce serait non_verifie")
    return problems


def rule_gaps(r: dict) -> list[str]:
    gaps = r.get("ecarts")
    if not isinstance(gaps, list):
        return ["ecarts doit être une liste"]
    problems = []
    for gap in gaps:
        if not isinstance(gap, dict) or set(gap) < {"champ", "etiquette", "catalogue"}:
            problems.append(f"écart mal formé : {gap!r} (attendu : champ, etiquette, catalogue)")
        elif gap["champ"] not in NUTRIENTS:
            problems.append(f"écart sur {gap['champ']!r} : ce n'est pas une clé de nutriment")
        elif any(gap[c] is not None and not is_number(gap[c]) for c in ("etiquette", "catalogue")):
            problems.append(f"écart sur {gap['champ']} : etiquette et catalogue sont des nombres ou null")
    return problems


def rule_alerts(r: dict) -> list[str]:
    alerts = r.get("alertes")
    if isinstance(alerts, list) and all(isinstance(x, str) for x in alerts):
        return []
    return ["alertes doit être une liste de textes"]


def rule_metrics(r: dict) -> list[str]:
    m = r.get("mesures")
    if not isinstance(m, dict):
        return ["mesures doit être un dictionnaire"]
    problems = _keys(m, METRICS)
    problems += [f"mesures.{k} = {m[k]!r} : un nombre" for k in METRICS if k in m and not is_number(m[k])]
    return problems


def rule_json(r: dict) -> list[str]:
    try:
        json.dumps(r)
    except (TypeError, ValueError) as e:
        return [f"le résultat ne passe pas en JSON (il doit pouvoir partir tel quel vers l'API) : {e}"]
    return []


RULES = {
    "status": rule_status, "product": rule_product, "base": rule_base, "nutrients": rule_nutrients,
    "less_than": rule_less_than, "ingredients": rule_ingredients, "status_and_sheet": rule_status_and_sheet,
    "unreadable": rule_unreadable, "gaps": rule_gaps, "alerts": rule_alerts, "metrics": rule_metrics,
    "json": rule_json,
}


def contract_problems(r: Any) -> list[str]:
    """Tous les écarts au contrat d'un résultat (liste vide = conforme)."""
    problems = rule_dictionary(r)
    if not isinstance(r, dict):
        return problems
    for rule in RULES.values():
        try:
            problems += rule(r)
        except Exception as e:  # résultat trop abîmé pour cette règle
            problems.append(f"{rule.__name__} : {type(e).__name__}: {e}")
    return problems
