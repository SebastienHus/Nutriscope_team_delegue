"""
Point d'entrée attendu par les outils de l'atelier (``tools/``) : ``src/scanner.py:scan_label``.

    pytest tools
    python tools/measure_scanner.py --version palier1

Le scanner lui-même est dans le paquet : ``nutriscope.scanner``.
"""

from nutriscope.scanner import scan_label

__all__ = ["scan_label"]
