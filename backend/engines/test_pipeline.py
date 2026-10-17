"""Full-pipeline integration: every Day 3 engine on the known fixtures.

The fixtures under ingest/fixtures have KNOWN ghost sets (pinned by
Day 2's money test). This test runs the whole Day 3 stack on them and
pins the report-level numbers, so a regression anywhere in the chain
shows up here first.
"""

import os

from engines import read_sources
from engines.report import build_report
from ingest.cli import analyze
from ingest.graph import add_resolved_edges, build_graph

FIXTURES = os.path.join(os.path.dirname(__file__), "..", "ingest", "fixtures")


def _report(name):
    root = os.path.join(FIXTURES, name)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    return build_report(records, graph, read_sources(root, records),
                        repo_label=name)


def test_py_app_full_pipeline():
    report = _report("py_app")
    assert report["summary"]["ghost_files"] == 1
    assert report["summary"]["ghost_symbols"] == 3
    ghost_files = [g["path"] for g in report["ghosts"]
                   if g["ghost_kind"] == "file"]
    assert ghost_files == ["truly_dead.py"]
    ghost_syms = {(g["path"], g["name"]) for g in report["ghosts"]
                  if g["ghost_kind"] == "symbol"}
    assert ghost_syms == {("utils.py", "stale"), ("pkg/core.py", "internal"),
                          ("truly_dead.py", "gone")}
    assert report["summary"]["annual_burn_usd"] > 0
    assert all(g["risk"] == "LOW" for g in report["ghosts"])


def test_js_app_full_pipeline():
    report = _report("js_app")
    assert report["summary"]["ghost_files"] == 1
    assert report["summary"]["ghost_symbols"] == 3
    ghost_files = [g["path"] for g in report["ghosts"]
                   if g["ghost_kind"] == "file"]
    assert ghost_files == ["orphan.js"]
    assert report["summary"]["annual_burn_usd"] > 0
    for ghost in report["ghosts"]:
        assert ghost["confidence"] >= 0.6  # no HIGH-risk flags on fixtures
        assert ghost["annual_saving_usd"] >= 0


def test_debt_sections_present_on_fixtures():
    report = _report("py_app")
    debt = report["debt"]
    assert debt["circular_imports"]["cycles"] == []
    assert debt["duplicates"] == []
    assert debt["huge_files"] == []
