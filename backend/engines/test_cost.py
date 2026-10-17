"""Cost model tests: complexity counting and the dollar math."""

from engines import read_sources
from engines.cost import (
    COST_PARAMS,
    annual_saving,
    complexity,
    file_mean_complexity,
    summarize,
)
from engines.deadcode import score_ghosts
from ingest.cli import analyze
from ingest.ghosts import detect_ghosts
from ingest.graph import add_resolved_edges, build_graph


def _write(tmp_path, rel, text):
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _pipeline(tmp_path):
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    ghosts = detect_ghosts(records, graph)
    sources = read_sources(root, records)
    return records, graph, score_ghosts(ghosts, records, sources), sources


def test_complexity_counts_branches():
    body = b"def f():\n    if a:\n        for x in y:\n            pass\n    return 1\n"
    assert complexity(body, "python") == 3
    assert complexity(b"def f():\n    return 1\n", "python") == 1


def test_complexity_js_operators():
    body = b"function f() { if (a && b) { return c ? d : e; } }"
    assert complexity(body, "javascript") == 4  # if, &&, ternary
    assert complexity(b"const f = () => a?.b ?? c;", "javascript") == 2


def test_file_mean_complexity(tmp_path):
    _write(tmp_path, "m.py",
           "def simple():\n    return 1\n\n"
           "def branchy():\n    if a:\n        return 1\n    return 2\n")
    records, _, _, sources = _pipeline(tmp_path)
    assert file_mean_complexity(records[0], sources) == 1.5


def test_annual_saving_math():
    # 10 lines at mean complexity 4: 10 x 0.50 x (1 + 0.15 x 4)
    assert annual_saving(10, 4.0) == 8.0
    assert annual_saving(0, 9.0) == 0.0


def test_summarize_end_to_end(tmp_path):
    _write(tmp_path, "main.py",
           'from live import run\n\nif __name__ == "__main__":\n    run()\n')
    _write(tmp_path, "live.py", "def run():\n    print('live')\n")
    _write(tmp_path, "dead.py",
           "def gone():\n    if True:\n        return 1\n    return 2\n"
           "\n\ndef plain():\n    return 0\n")
    records, graph, scored, sources = _pipeline(tmp_path)
    summary = summarize(scored, records, graph, sources)
    by_key = {(g["ghost_kind"], g.get("name") or g["path"]): g
              for g in summary["ghosts"]}
    file_ghost = by_key[("file", "dead.py")]
    gone = by_key[("symbol", "gone")]
    plain = by_key[("symbol", "plain")]
    # dead.py: 8 lines, mean complexity 1.5 -> 8 x 0.50 x 1.225
    assert file_ghost["loc"] == 8
    assert file_ghost["annual_saving_usd"] == 4.9
    # gone(): 4 lines, complexity 2 -> 4 x 0.50 x 1.30
    assert gone["loc"] == 4
    assert gone["annual_saving_usd"] == 2.6
    # plain(): 2 lines, complexity 1 -> 2 x 0.50 x 1.15
    assert plain["loc"] == 2
    assert plain["annual_saving_usd"] == 1.15
    assert summary["annual_burn_usd"] == 8.65
    assert summary["ghost_loc"] == 14
    assert summary["params"] == COST_PARAMS
    # Biggest saving first: the dashboard's $ Saved column sorts itself.
    savings = [g["annual_saving_usd"] for g in summary["ghosts"]]
    assert savings == sorted(savings, reverse=True)
