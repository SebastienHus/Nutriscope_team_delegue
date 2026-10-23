"""`python -m nutriscope` : raccourci vers `python -m nutriscope.pipeline`."""

import sys

from .pipeline import main

sys.exit(main())
