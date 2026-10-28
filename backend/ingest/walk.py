"""Bounded walk over a repo checkout, yielding supported source files.

Caps are a security baseline, not tuning: analysis must fail with a clean
error instead of hanging the worker on a pathological checkout.
"""

import os

from api.security import env_int
from .extract import detect_language

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".tox",
    "dist", "build", ".next", ".pytest_cache", ".mypy_cache",
}

# ponytail: reuse api.security.env_int (stdlib-only, no import cycle):
# a mistyped operator value used to raise ValueError at import and take
# the whole API down at boot; now it logs a warning and uses the default.
MAX_FILES = env_int("GHOSTCODE_MAX_FILES", 20000)
MAX_FILE_BYTES = env_int("GHOSTCODE_MAX_FILE_BYTES", 1000000)


class WalkError(Exception):
    pass


def walk_repo(root):
    """Yield (relpath, abspath, language) for every supported source file.

    Raises WalkError when the root is unusable or the file cap is exceeded.
    """
    root = os.path.realpath(root)
    if not os.path.isdir(root):
        raise WalkError(f"not a directory: {root}")

    found = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        for filename in sorted(filenames):
            language = detect_language(filename)
            if language is None:
                continue
            abspath = os.path.join(dirpath, filename)
            if os.path.getsize(abspath) > MAX_FILE_BYTES:
                continue
            found.append((os.path.relpath(abspath, root), abspath, language))
            if len(found) > MAX_FILES:
                raise WalkError(
                    f"repo exceeds the {MAX_FILES}-file analysis cap"
                )
    return found
