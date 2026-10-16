"""Entry-point analysis and ghost detection.

A ghost is a node with no incoming edges after entry-point analysis:
nothing imports it, nothing calls it, and it is not a known entry point
(scripts, tests, package surface). The one-line reason on each ghost is
deliberate: Day 3's risk scoring needs something to show, not just a flag.

Entry rules (v1, app-oriented; tuned against real repos on Day 7):
- Python: `if __name__ == "__main__"` scripts, `__main__.py`,
  `__init__.py` (package surface), test files.
- JS/TS: test files, root-level index.* (the bundler-convention app entry).
- Any language: a file that defines nothing but calls things is run,
  not imported. Kept tight on purpose: a constants file with no calls
  stays flaggable.
"""

import os

from . import schema
from .graph import file_id

_TEST_DIRNAMES = {"tests", "test", "__tests__"}
_JS_ROOT_ENTRIES = {"index.js", "index.jsx", "index.ts", "index.tsx"}


def _parts(path):
    return path.replace(os.sep, "/").split("/")


def _is_test_file(path):
    parts = _parts(path)
    if any(part in _TEST_DIRNAMES for part in parts[:-1]):
        return True
    stem = parts[-1]
    return (stem.startswith("test_") or stem.endswith("_test.py")
            or ".test." in stem or ".spec." in stem)


def entry_files(records):
    """Repo-relative paths that are program entry points, never ghosts."""
    entries = set()
    for record in records:
        path = record["path"]
        base = _parts(path)[-1]
        if record.get("has_main_guard"):
            entries.add(path)
        elif base in ("__main__.py", "__init__.py"):
            entries.add(path)
        elif _is_test_file(path):
            # The test runner invokes these; no static call edge exists.
            entries.add(path)
        elif (record["language"] in ("javascript", "typescript", "tsx")
              and len(_parts(path)) == 1 and base in _JS_ROOT_ENTRIES):
            entries.add(path)
        elif not record["defs"] and record["calls"]:
            entries.add(path)
    return entries


def live_symbols(records, graph):
    """Symbol node ids that are live regardless of incoming edges."""
    index = graph.graph.get("symbol_index", {})
    by_path = {r["path"]: r for r in records}
    tests = {path for path in by_path if _is_test_file(path)}
    live = set()
    for (path, _kind, name), ids in index.items():
        if name.startswith("__") and name.endswith("__") and len(name) > 4:
            # Dunders are invoked by the runtime, never called by name.
            live.update(ids)
        elif path in tests:
            # Test functions are discovered by the runner, not called
            # in code; without this every test would be a ghost.
            live.update(ids)
    return live


def detect_ghosts(records, graph):
    """Return the versioned ghost report for a resolved graph."""
    entries = entry_files(records)
    live = live_symbols(records, graph)
    files, symbols = [], []
    for record in records:
        if record["path"] in entries:
            continue
        fid = file_id(record["path"])
        incoming = [d for _, _, d in graph.in_edges(fid, data=True)]
        if not any(d.get("type") == "imports_resolved" for d in incoming):
            files.append({
                "path": record["path"],
                "reason": "no incoming imports and not an entry point",
            })
    for node, attrs in graph.nodes(data=True):
        if attrs.get("kind") != "symbol" or node in live:
            continue
        incoming = [d for _, _, d in graph.in_edges(node, data=True)]
        if not any(d.get("type") in ("call", "uses") for d in incoming):
            symbols.append({
                "id": node,
                "path": attrs.get("file"),
                "kind": attrs.get("sym_kind"),
                "name": attrs.get("name"),
                "reason": "no incoming calls or named imports",
            })
    files.sort(key=lambda f: f["path"])
    symbols.sort(key=lambda s: (s["path"] or "", s["name"] or ""))
    return {"schema": schema.SCHEMA_VERSION, "files": files, "symbols": symbols}
