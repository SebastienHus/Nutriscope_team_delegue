"""
Scanner d'étiquettes (atelier du TP 18) : la photo d'un emballage -> le dictionnaire du contrat.

Le workflow est écrit ici, en code ; le modèle de vision ne fait que lire la photo :

    image ──► URL data: ──► lecture(s) ──► validation (+ relances) ──► vote ──► catalogue ──► résultat
                 │ illisible                  │ JSON / contrôles                  │ chercher_produit
                 └► "illisible"               └► champs écartés + alertes        └► verifie / non_verifie

Réglages (environnement) : ``SCANNER_READS`` (lectures par photo, 1 par défaut),
``SCANNER_MODELS`` (modèles de vision séparés par des virgules, utilisés à tour de rôle ;
le modèle de vision de la configuration par défaut), ``SCANNER_RETRIES`` (relances d'une lecture invalide, 1 par
défaut), ``SCANNER_MAX_SIDE`` (pixels, 1200 par défaut).

    from nutriscope.scanner import scanner_etiquette
    scanner_etiquette("data/photos/10_3608580065340_etiquette.jpg")

``scanner_etiquette`` ne lève jamais d'exception : une image illisible, un JSON mal formé ou un
modèle qui ne répond pas donnent quand même un résultat conforme au contrat, avec des alertes.

Photos : contributeurs Open Food Facts, CC-BY-SA 3.0 (data/sources_photos.csv). Données : ODbL.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any

from ..assistant.client import describe_error, make_client
from ..assistant.config import LLMConfig, load_config
from .answer import ReviewedAnswer, answer_question
from .image import UnreadableImage, to_data_url
from .reading import ReadMeasures, read_label
from .routing import differences, find_sheet
from .validation import NUTRIENTS, Reading
from .vote import vote

__all__ = ["LabelScanner", "ReviewedAnswer", "answer_question", "empty_result", "scan_label"]

log = logging.getLogger(__name__)
SEARCH_TOOL = "chercher_produit"


def empty_result(alerts: list[str] | None = None) -> dict[str, Any]:
    """Un résultat "illisible" conforme au contrat."""
    return {
        "statut": "illisible",
        "produit": {"nom": None, "marque": None, "code_barres": None},
        "base": None,
        "nutriments": dict.fromkeys(NUTRIENTS),
        "inferieur_a": [],
        "ingredients": None,
        "fiche_catalogue": None,
        "ecarts": [],
        "alertes": list(alerts or []),
        "mesures": {"appels_modele": 0, "latence_s": 0.0, "tokens_entree": 0, "tokens_sortie": 0},
    }


class LabelScanner:
    """Le scanner et ses dépendances. ``scanner(image)`` rend le dictionnaire du contrat."""

    def __init__(self, registry=None, client=None, config: LLMConfig | None = None,
                 reads: int | None = None, models: list[str] | None = None, max_retries: int | None = None):
        self.config = config or load_config()
        self.client = client if client is not None else make_client(self.config)
        self.registry = registry                 # None : construit au premier besoin sur le catalogue PostgreSQL
        self.reads = max(1, reads or int(os.getenv("SCANNER_READS") or 1))
        env_models = [m.strip() for m in (os.getenv("SCANNER_MODELS") or "").split(",") if m.strip()]
        self.models = models or env_models or [self.config.vision_model]
        self.max_retries = max_retries if max_retries is not None else int(os.getenv("SCANNER_RETRIES") or 1)

    # -- catalogue ---------------------------------------------------------

    def _search(self, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.registry is None:
            from ..catalog import default_catalog
            from ..tools import ToolContext, ToolRegistry

            self.registry = ToolRegistry.discover(ToolContext(catalog=default_catalog()))
        return self.registry.run(SEARCH_TOOL, arguments)

    # -- workflow ------------------------------------------------------------

    def __call__(self, image: Any, face: Any = None) -> dict[str, Any]:
        """
        ``image`` : photo du tableau nutritionnel (chemin ou octets). ``face`` : photo de la face avant,
        facultative ; envoyée dans la même lecture, elle aide à lire le nom, la marque et le code-barres.
        """
        start = time.perf_counter()
        measures = ReadMeasures()
        try:
            result = self._scan(image, measures, face)
        except Exception as exc:     # le contrat interdit les exceptions
            log.exception("scanner failed")
            result = empty_result([f"erreur inattendue du scanner ({type(exc).__name__})"])
        result["mesures"] = {"appels_modele": measures.calls, "latence_s": round(time.perf_counter() - start, 3),
                             "tokens_entree": measures.input_tokens, "tokens_sortie": measures.output_tokens}
        return result

    def _scan(self, image: Any, measures: ReadMeasures, face: Any = None) -> dict[str, Any]:
        try:
            data_urls = [to_data_url(image)[0]]
        except UnreadableImage as exc:
            return empty_result([str(exc)])
        alerts: list[str] = []
        if face is not None:
            try:
                data_urls.append(to_data_url(face)[0])
            except UnreadableImage as exc:
                alerts.append(f"face avant ignorée : {exc}")

        # 1-2. Lire et valider, éventuellement plusieurs fois (vote)
        readings: list[Reading] = []
        for index in range(self.reads):
            model = self.models[index % len(self.models)]
            try:
                outcome = read_label(self.client, self.config, data_urls, model=model, max_retries=self.max_retries)
            except Exception as exc:  # modèle absent du serveur, injoignable, délai dépassé
                alerts.append(f"modèle {model} indisponible ({describe_error(exc)})")
                continue
            measures.add(outcome.measures)
            alerts += outcome.alerts
            if outcome.reading is not None:
                readings.append(outcome.reading)
        if not readings:
            return empty_result(alerts or ["aucune lecture exploitable"])
        reading = vote(readings)
        alerts = reading.alerts + [a for a in alerts if a not in reading.alerts]

        identified = any((reading.nom, reading.marque, reading.code_barres))
        if not identified and not reading.has_values:
            result = empty_result(alerts + ["aucun produit identifié et aucune valeur lue"])
            result["ingredients"] = reading.ingredients
            return result

        # 3. Aiguiller vers le catalogue
        sheet, routing_alerts = (None, [])
        try:
            sheet, routing_alerts = find_sheet(reading, self._search)
        except Exception as exc:  # catalogue indisponible
            routing_alerts = [f"catalogue indisponible ({type(exc).__name__}) : lecture non vérifiée"]
        alerts += routing_alerts
        gaps = differences(reading, sheet) if sheet else []
        if sheet and reading.base == "100 ml":
            alerts.append("valeurs pour 100 ml comparées à une fiche pour 100 g/100 ml : écarts à lire avec prudence")

        return {
            "statut": "verifie" if sheet else "non_verifie",
            "produit": {"nom": reading.nom, "marque": reading.marque, "code_barres": reading.code_barres},
            "base": reading.base,
            "nutriments": dict(reading.nutriments),
            "inferieur_a": [key for key in reading.inferieur_a if reading.nutriments.get(key) is not None],
            "ingredients": reading.ingredients,
            "fiche_catalogue": sheet,
            "ecarts": gaps,
            "alertes": alerts,
            "mesures": {},
        }


_default_scanner: LabelScanner | None = None


def scan_label(image: Any, face: Any = None) -> dict[str, Any]:
    """
    Chemin ou octets d'une photo -> dictionnaire résultat. ``face`` :
    photo de la face avant. Ne lève jamais d'exception.
    """
    global _default_scanner
    if _default_scanner is None:
        try:
            _default_scanner = LabelScanner()
        except Exception as exc:     # configuration manquante
            return empty_result([f"scanner non configuré ({type(exc).__name__}: {exc})"])
    return _default_scanner(image, face)
