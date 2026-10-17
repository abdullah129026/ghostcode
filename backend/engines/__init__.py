"""Shared helpers for the GhostCode analysis engines."""

import os


def read_sources(root, records):
    """Map repo-relative path -> file bytes for every record we can read.

    Engines work off records, but a few checks (string references, body
    hashing) need the raw text. Missing files are skipped, never fatal.
    """
    sources = {}
    for record in records:
        path = os.path.join(root, record["path"])
        try:
            with open(path, "rb") as handle:
                sources[record["path"]] = handle.read()
        except OSError:
            continue
    return sources
