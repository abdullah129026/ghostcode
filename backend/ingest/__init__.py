"""GhostCode ingestion: tree-sitter symbol extraction for Python and JS/TS.

Produces per-file symbol records (imports, definitions, exports, call
references). Call edges are resolved by the graph layer; this package only
records what each file says about itself.
"""

__version__ = "0.1.0"

from .extract import extract_file, detect_language
from .walk import walk_repo
from .schema import SCHEMA_VERSION

__all__ = ["extract_file", "detect_language", "walk_repo", "SCHEMA_VERSION"]
