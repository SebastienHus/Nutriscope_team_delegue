"""
Point d'entrée attendu par les outils de l'atelier (``outils/``) : ``src/scanner.py:scanner_etiquette``.

    pytest outils
    python outils/mesurer_scanner.py --version palier1

Le scanner lui-même est dans le paquet : ``nutriscope.scanner``.
"""

from nutriscope.scanner import scanner_etiquette

__all__ = ["scanner_etiquette"]
