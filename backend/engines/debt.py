"""Structural debt signals: what makes the codebase expensive to keep.

Three checks, each cheap and each tuned for a low false-positive bar:
- circular imports: real import cycles between files, from the resolved
  import edges. Reported smallest-first, capped so a tangled repo cannot
  blow up the report.
- duplicated logic: function/method bodies hashed after normalizing
  whitespace and dropping blank and full-line comments. Only exact
  normalized duplicates count, so near-misses never flag.
- huge files: files over HUGE_FILE_LOC lines, the maintenance sink.
"""

import hashlib

import networkx as nx

from ingest.graph import file_id

MAX_REPORTED_CYCLES = 25
HUGE_FILE_LOC = 800
MIN_DUP_LINES = 5

_COMMENT_PREFIXES = (b"#", b"//", b"/*", b"*")


def circular_imports(graph):
    """Import cycles between files, normalized for deterministic output."""
    files = nx.DiGraph()
    for src, dst, data in graph.edges(data=True):
        if data.get("type") != "imports_resolved":
            continue
        if graph.nodes[src].get("kind") == "file" and graph.nodes[dst].get("kind") == "file":
            files.add_edge(src, dst)
    cycles = []
    for cycle in nx.simple_cycles(files):
        # Rotate so the smallest path starts the cycle, then sort cycles:
        # the same logical cycle always prints the same way.
        paths = [graph.nodes[n]["path"] for n in cycle]
        i = paths.index(min(paths))
        cycles.append(paths[i:] + paths[:i])
    cycles.sort()
    truncated = len(cycles) > MAX_REPORTED_CYCLES
    return {"cycles": cycles[:MAX_REPORTED_CYCLES], "truncated": truncated}


def _normalized_body(source, lineno, end_lineno):
    lines = source.split(b"\n")[lineno - 1 : end_lineno]
    code = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(_COMMENT_PREFIXES):
            continue
        code.append(b" ".join(stripped.split()))
    return b"\n".join(code), len(code)


def duplicate_bodies(records, sources, min_lines=MIN_DUP_LINES):
    """Groups of functions/methods with identical normalized bodies."""
    by_hash = {}
    for record in records:
        source = sources.get(record["path"])
        if source is None:
            continue
        for definition in record["defs"]:
            if definition["kind"] not in ("function", "method"):
                continue
            body, nlines = _normalized_body(
                source, definition["lineno"], definition["end_lineno"]
            )
            if nlines < min_lines:
                continue
            digest = hashlib.sha256(body).hexdigest()
            by_hash.setdefault(digest, []).append(
                {
                    "path": record["path"],
                    "kind": definition["kind"],
                    "name": definition["name"],
                    "lines": nlines,
                }
            )
    groups = [members for members in by_hash.values() if len(members) > 1]
    for members in groups:
        members.sort(key=lambda m: (m["path"], m["name"]))
    groups.sort(key=lambda g: (g[0]["path"], g[0]["name"]))
    return groups


def huge_files(records, threshold=HUGE_FILE_LOC):
    """Files at or over the huge-file line budget, largest first."""
    flagged = [
        {"path": r["path"], "loc": r["loc"], "over_by": r["loc"] - threshold}
        for r in records
        if r["loc"] >= threshold
    ]
    flagged.sort(key=lambda f: -f["loc"])
    return flagged


def analyze_debt(records, graph, sources):
    """Run all three debt checks, one dict for the report."""
    return {
        "circular_imports": circular_imports(graph),
        "duplicates": duplicate_bodies(records, sources),
        "huge_files": huge_files(records),
    }
