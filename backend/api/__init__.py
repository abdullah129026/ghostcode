"""GhostCode HTTP API (Day 4): FastAPI over the analysis pipeline.

Running under uvicorn or pytest, ``backend/`` must be importable so the
sibling ``ingest`` and ``engines`` packages resolve. This insert makes
that true no matter the entrypoint; it is a no-op when already present.
"""

import os
import sys

_BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)
