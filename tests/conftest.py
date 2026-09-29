"""
Configuration pytest pour le module de nettoyage — TP 9
"""

import sys
from pathlib import Path

# Ajouter src/ au path pour importer cleaning et report
ROOT = Path(__file__).parent.parent / "src"
print(ROOT)
sys.path.insert(0, str(ROOT))
