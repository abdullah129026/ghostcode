"""Debt engine tests: cycles, duplicate bodies, huge files."""

from engines import read_sources
from engines.debt import (
    analyze_debt,
    circular_imports,
    duplicate_bodies,
    huge_files,
)
from ingest.cli import analyze
from ingest.graph import add_resolved_edges, build_graph

DUP_BODY = """def clone():
    total = 0
    for i in range(10):
        total += i * 2
    if total > 5:
        total -= 1
    return total
"""


def _write(tmp_path, rel, text):
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _pipeline(tmp_path):
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    return records, graph, read_sources(root, records)


def test_circular_import_found(tmp_path):
    _write(tmp_path, "a.py", "import b\n\ndef fa():\n    return b.fb()\n")
    _write(tmp_path, "b.py", "import a\n\ndef fb():\n    return 1\n")
    records, graph, _ = _pipeline(tmp_path)
    result = circular_imports(graph)
    assert result["cycles"] == [["a.py", "b.py"]]
    assert result["truncated"] is False


def test_no_cycle_no_report(tmp_path):
    _write(tmp_path, "a.py", "import b\n\ndef fa():\n    return b.fb()\n")
    _write(tmp_path, "b.py", "def fb():\n    return 1\n")
    records, graph, _ = _pipeline(tmp_path)
    assert circular_imports(graph)["cycles"] == []


def test_duplicate_bodies_grouped(tmp_path):
    _write(tmp_path, "one.py", DUP_BODY)
    _write(tmp_path, "two.py", "# a comment\n" + DUP_BODY)
    _write(tmp_path, "three.py", "def other():\n    return 42\n")
    records, _, sources = _pipeline(tmp_path)
    groups = duplicate_bodies(records, sources)
    assert len(groups) == 1
    assert {(m["path"], m["name"]) for m in groups[0]} == {
        ("one.py", "clone"),
        ("two.py", "clone"),
    }


def test_tiny_bodies_not_flagged(tmp_path):
    tiny = "def f():\n    return 1\n"
    _write(tmp_path, "one.py", tiny)
    _write(tmp_path, "two.py", tiny)
    records, _, sources = _pipeline(tmp_path)
    assert duplicate_bodies(records, sources) == []


def test_huge_file_flagged(tmp_path):
    _write(tmp_path, "big.py", "\n".join(f"x{i} = {i}" for i in range(900)))
    _write(tmp_path, "small.py", "x = 1\n")
    records, _, _ = _pipeline(tmp_path)
    flagged = huge_files(records, threshold=800)
    assert [f["path"] for f in flagged] == ["big.py"]
    assert flagged[0]["over_by"] == flagged[0]["loc"] - 800


def test_analyze_debt_shape(tmp_path):
    _write(tmp_path, "a.py", "import b\n")
    _write(tmp_path, "b.py", "import a\n")
    records, graph, sources = _pipeline(tmp_path)
    debt = analyze_debt(records, graph, sources)
    assert set(debt) == {"circular_imports", "duplicates", "huge_files"}
    assert debt["circular_imports"]["cycles"] == [["a.py", "b.py"]]


def test_duplicate_bodies_skips_missing_sources_and_non_functions():
    """Records without source, and defs that are not functions or methods,
    are skipped; blank lines and comments inside a body are ignored when
    normalizing, so two copies still group together."""
    body = (
        b"def clone():\n"
        b"    total = 0\n"
        b"\n"
        b"    # running total\n"
        b"    for i in range(10):\n"
        b"        total += i * 2\n"
        b"    if total > 5:\n"
        b"        total -= 1\n"
        b"    return total\n"
    )
    records = [
        {"path": "gone.py", "defs": [
            {"kind": "function", "name": "clone", "lineno": 1,
             "end_lineno": 9}]},
        {"path": "mixed.py", "defs": [
            {"kind": "class", "name": "Widget", "lineno": 1,
             "end_lineno": 9},
            {"kind": "function", "name": "clone", "lineno": 1,
             "end_lineno": 9}]},
        {"path": "other.py", "defs": [
            {"kind": "function", "name": "clone", "lineno": 1,
             "end_lineno": 9}]},
    ]
    sources = {"mixed.py": body, "other.py": body}
    groups = duplicate_bodies(records, sources)
    assert len(groups) == 1
    assert {(m["path"], m["name"]) for m in groups[0]} == {
        ("mixed.py", "clone"), ("other.py", "clone")}
