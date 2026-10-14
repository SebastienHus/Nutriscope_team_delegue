"""Permet aussi `python -m nutriscope <commande>` (équivalent à `python -m nutriscope.pipeline`)."""
import sys

from nutriscope.pipeline import main

sys.exit(main())
