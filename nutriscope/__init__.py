"""
NutriScope — pipeline bout-en-bout du TP 13 (jalon J3).

Une commande unique, du CSV Open Food Facts brut aux données prêtes pour le ML :

    python -m nutriscope.pipeline all

Cinq étapes, lançables seules : charger, nettoyer, charger_base, parquet, exports.
Le code des TP 9 et 12 (`src/`) n'est pas modifié : il est importé (voir `nutriscope/legacy.py`).

Données : © Open Food Facts contributors — ODbL.
"""

__version__ = "0.3.0"
