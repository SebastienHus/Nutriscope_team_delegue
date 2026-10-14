"""
Accès au code existant des TP 9 et 12 (`src/`), sans le modifier ni le recopier.

Les modules de `src/` s'importent « à plat » (`import cleaning`, `from storage.convert_parquet import …`).
On ajoute donc `src/` au chemin d'import une seule fois, à partir de l'emplacement du dépôt.

Attention : `src/pipeline.py` (TP 9) existe. Dans ce projet, on écrit toujours `nutriscope.pipeline`,
jamais `import pipeline`, pour ne pas confondre les deux.
"""

import sys

from nutriscope.config import ROOT

SRC = ROOT / "src"


def ensure_src_on_path() -> None:
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))


ensure_src_on_path()
