"""Configuration des tests du contrat : l'option --scanner et le chargement de votre fonction.

Lancement, depuis la racine de votre dépôt :

    pytest scan_tools
    pytest scan_tools --scanner src/workflow.py:scan_label     # si votre fonction est ailleurs
"""

from __future__ import annotations

from typing import Any

import pytest

from scan_common import DEFAULT_SCANNER, ScannerNotFound, load_scanner


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--scanner", default=DEFAULT_SCANNER,
                     help=f"où est votre fonction : fichier.py:nom_fonction (défaut : {DEFAULT_SCANNER})")


@pytest.fixture(scope="session")
def scan_label(request: pytest.FixtureRequest):
    """Sans scanner, inutile de lancer 90 tests : un seul message clair, et on s'arrête."""
    # L'option n'existe pas si pytest est lancé sans « scan_tools » en argument : on prend alors le défaut.
    target = request.config.getoption("--scanner", default=DEFAULT_SCANNER)
    try:
        return load_scanner(target)
    except ScannerNotFound as e:
        pytest.exit(f"Scanner introuvable : {e}", returncode=2)


@pytest.fixture(scope="session")
def scan_once(scan_label):
    """Chaque image n'est scannée qu'une fois, quel que soit le nombre de tests qui l'utilisent."""
    cache: dict[str, Any] = {}

    def scan(key: str, image: Any) -> Any:
        if key not in cache:
            try:
                cache[key] = ("ok", scan_label(image))
            except Exception as e:
                cache[key] = ("exception", f"{type(e).__name__}: {e}")
        state, value = cache[key]
        if state == "exception":
            pytest.fail(f"scan_label a levé une exception (le contrat l'interdit) : {value}", pytrace=False)
        return value

    return scan
