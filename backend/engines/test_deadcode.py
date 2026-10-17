"""Dead-code scorer tests: confidence, risk levels, and reasons.

The scorer's contract: every ghost gets a confidence, a LOW/MED/HIGH
risk, and human-readable reasons. Tests pin the base numbers and each
penalty using tiny synthetic repos run through the real pipeline.
"""

from engines import read_sources
from engines.deadcode import score_ghosts
from ingest.cli import analyze
from ingest.ghosts import detect_ghosts
from ingest.graph import add_resolved_edges, build_graph

MAIN = 'from live import run\n\nif __name__ == "__main__":\n    run()\n'
LIVE = "def run():\n    print('live')\n"
DEAD = "def gone():\n    return 1\n"


def _repo(tmp_path, extra=None):
    (tmp_path / "main.py").write_text(MAIN)
    (tmp_path / "live.py").write_text(LIVE)
    (tmp_path / "dead.py").write_text(DEAD)
    for rel, text in (extra or {}).items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    return records, graph, detect_ghosts(records, graph), read_sources(root, records)


def _file_ghost(scored, path):
    return next(g for g in scored if g["ghost_kind"] == "file"
                and g["path"] == path)


def test_clean_repo_file_ghost_is_low_risk(tmp_path):
    records, graph, ghosts, sources = _repo(tmp_path)
    scored = score_ghosts(ghosts, records, sources)
    file_ghost = _file_ghost(scored, "dead.py")
    assert file_ghost["ghost_kind"] == "file"
    assert file_ghost["confidence"] == 0.95
    assert file_ghost["risk"] == "LOW"
    assert file_ghost["reasons"][0] == "no incoming imports and not an entry point"
    assert any("deletes as one unit" in r for r in file_ghost["reasons"])


def test_clean_repo_symbol_ghost_scores_base(tmp_path):
    records, graph, ghosts, sources = _repo(tmp_path)
    scored = score_ghosts(ghosts, records, sources)
    sym = next(g for g in scored if g["ghost_kind"] == "symbol")
    assert sym["name"] == "gone"
    assert sym["confidence"] == 0.90
    assert sym["risk"] == "LOW"
    # Safest deletes come first: the whole file outranks the stray symbol.
    assert scored[0]["path"] == "dead.py"


def test_string_reference_dings_symbol_confidence(tmp_path):
    records, graph, ghosts, sources = _repo(
        tmp_path, {"main.py": MAIN + '\nhandler = "gone"\n'}
    )
    scored = score_ghosts(ghosts, records, sources)
    sym = next(g for g in scored if g["ghost_kind"] == "symbol")
    assert sym["confidence"] == 0.65
    assert sym["risk"] == "MED"
    assert any("string literal" in r for r in sym["reasons"])
    # The file ghost is unaffected: 'gone' is a symbol name, not a file name.
    assert _file_ghost(scored, "dead.py")["confidence"] == 0.95


def test_dynamic_dispatch_flags_repo(tmp_path):
    records, graph, ghosts, sources = _repo(
        tmp_path, {"live.py": LIVE + '\nmode = getattr(run, "x", None)\n'}
    )
    scored = score_ghosts(ghosts, records, sources)
    assert all("dynamic dispatch" in " ".join(g["reasons"]) for g in scored)
    file_ghost = next(g for g in scored if g["ghost_kind"] == "file")
    assert file_ghost["confidence"] == 0.80
    assert file_ghost["risk"] == "MED"


def test_wildcard_import_flags_repo(tmp_path):
    records, graph, ghosts, sources = _repo(
        tmp_path, {"live.py": "from dead import *\n" + LIVE}
    )
    scored = score_ghosts(ghosts, records, sources)
    assert all("wildcard" in " ".join(g["reasons"]) for g in scored)
