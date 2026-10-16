"""Day 2 graph tests: resolution, entry points, and ghost detection.

The fixture repos under fixtures/ are the money test: hand-built apps
with KNOWN ghost sets. Exact assertions, no maybes. See fixtures/README.md
for the rules each fixture pins down.
"""

import os

from ingest import schema
from ingest.cli import analyze
from ingest.ghosts import detect_ghosts, entry_files, live_symbols
from ingest.graph import add_resolved_edges, build_graph
from ingest.resolve import call_edges, import_edges, resolve_module, use_edges

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _norm_path(path):
    return path.replace(os.sep, "/")


def _fixture_ghosts(name):
    root = os.path.join(FIXTURES, name)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    return detect_ghosts(records, graph)


def test_python_fixture_exact_ghost_set():
    report = _fixture_ghosts("py_app")
    assert report["schema"] == 1
    assert [_norm_path(f["path"]) for f in report["files"]] == ["truly_dead.py"]
    got = {(_norm_path(s["path"]), s["name"]) for s in report["symbols"]}
    assert got == {("utils.py", "stale"), ("pkg/core.py", "internal"),
                   ("truly_dead.py", "gone")}


def test_js_fixture_exact_ghost_set():
    report = _fixture_ghosts("js_app")
    assert report["schema"] == 1
    assert [_norm_path(f["path"]) for f in report["files"]] == ["orphan.js"]
    got = {(_norm_path(s["path"]), s["name"]) for s in report["symbols"]}
    assert got == {("lib.js", "unused"), ("cjs.js", "stringify"),
                   ("orphan.js", "lost")}


def test_resolve_python_absolute_and_relative(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "core.py").write_text("")
    root = str(tmp_path)
    assert resolve_module(root, "main.py", "python", "pkg") == ["pkg/__init__.py"]
    assert resolve_module(root, "main.py", "python", "pkg.core") == ["pkg/core.py"]
    assert resolve_module(root, "pkg/__init__.py", "python", ".core") == ["pkg/core.py"]
    assert resolve_module(root, "main.py", "python", "os") == []  # stdlib: external
    assert resolve_module(root, "main.py", "python", "nope") == []


def test_resolve_js_relative_and_bare(tmp_path):
    (tmp_path / "lib.ts").write_text("")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "index.js").write_text("")
    root = str(tmp_path)
    assert resolve_module(root, "index.js", "javascript", "./lib") == ["lib.ts"]
    assert resolve_module(root, "index.js", "javascript", "./sub") == ["sub/index.js"]
    assert resolve_module(root, "index.js", "javascript", "react") == []  # bare: external


def test_import_edges_include_parent_packages(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "core.py").write_text("")
    root = str(tmp_path)
    records = [{
        "path": "pkg/__init__.py", "language": "python", "loc": 1,
        "imports": [{"module": ".core", "names": [{"name": "api", "alias": None}],
                     "alias": None, "lineno": 1, "kind": "from"}],
        "defs": [], "exports": [], "calls": [],
        "has_main_guard": False, "default_export": None,
    }]
    edges = import_edges(root, records)
    assert ("pkg/__init__.py", "pkg/core.py", "from") in edges


def _record(path, language="python", defs=(), imports=(), calls=(),
            has_main_guard=False, default_export=None):
    return schema.file_record(path, language, 10, list(imports), list(defs),
                              [], list(calls), has_main_guard=has_main_guard,
                              default_export=default_export)


def test_call_edges_same_file():
    records = [_record(
        "a.py",
        defs=[schema.def_record("function", "f", 1, 3),
              schema.def_record("function", "g", 4, 5)],
        calls=[schema.call_record("f", None, 5)],
    )]
    edges = call_edges("/nonexistent", records)
    assert ("a.py", "a.py", "function", "f", "call") in edges
    assert not any(e[3] == "g" for e in edges)


def test_call_edges_method_receiver_keeps_live():
    records = [_record(
        "a.py",
        defs=[schema.def_record("class", "Widget", 1, 9),
              schema.def_record("method", "render", 2, 4, parent="Widget")],
        calls=[schema.call_record("render", "widget", 8)],
    )]
    edges = call_edges("/nonexistent", records)
    assert ("a.py", "a.py", "method", "render", "call") in edges


def test_call_edges_cross_file_named_import(tmp_path):
    (tmp_path / "lib.py").write_text("")
    root = str(tmp_path)
    records = [
        _record("lib.py", defs=[schema.def_record("function", "used", 1, 2)]),
        _record("app.py",
                imports=[schema.import_record("lib", names=[{"name": "used", "alias": None}],
                                              kind="from")],
                calls=[schema.call_record("used", None, 3)]),
    ]
    edges = call_edges(root, records)
    assert ("app.py", "lib.py", "function", "used", "call") in edges


def test_use_edges_named_import_counts_as_use(tmp_path):
    (tmp_path / "lib.py").write_text("")
    root = str(tmp_path)
    records = [
        _record("lib.py", defs=[schema.def_record("function", "kept", 1, 2)]),
        _record("app.py",
                imports=[schema.import_record("lib", names=[{"name": "kept", "alias": None}],
                                              kind="from")]),
    ]
    edges = use_edges(root, records)
    assert ("app.py", "lib.py", "function", "kept", "uses") in edges


def test_use_edges_default_import(tmp_path):
    (tmp_path / "view.js").write_text("")
    root = str(tmp_path)
    records = [
        _record("view.js", language="javascript",
                defs=[schema.def_record("function", "render", 1, 3)],
                default_export="render"),
        _record("index.js", language="javascript",
                imports=[{**schema.import_record("./view.js", kind="from"),
                          "default": "render"}]),
    ]
    edges = use_edges(root, records)
    assert ("index.js", "view.js", "function", "render", "uses") in edges


def test_entry_files():
    records = [
        _record("run.py", has_main_guard=True),
        _record("pkg/__init__.py"),
        _record("tests/test_x.py", calls=[schema.call_record("f", None, 1)]),
        _record("index.js", language="javascript"),
        _record("script.py", calls=[schema.call_record("f", None, 1)]),
        _record("lib.py", defs=[schema.def_record("function", "f", 1, 2)]),
        _record("constants.py"),  # no defs, no calls: stays flaggable
    ]
    entries = entry_files(records)
    assert entries == {"run.py", "pkg/__init__.py", "tests/test_x.py",
                       "index.js", "script.py"}


def test_live_symbols_dunder_and_tests():
    records = [
        _record("a.py", defs=[schema.def_record("method", "__repr__", 1, 2),
                              schema.def_record("function", "dead", 3, 4)]),
        _record("test_a.py", defs=[schema.def_record("function", "test_x", 1, 2)]),
    ]
    graph = build_graph(records)
    live = live_symbols(records, graph)
    by_name = {}
    for (path, kind, name), ids in graph.graph["symbol_index"].items():
        by_name[name] = set(ids)
    assert by_name["__repr__"] <= live
    assert by_name["test_x"] <= live
    assert not (by_name["dead"] & live)


def test_detect_ghosts_smoke(tmp_path):
    (tmp_path / "used.py").write_text("")
    (tmp_path / "dead.py").write_text("")
    root = str(tmp_path)
    records = [
        _record("used.py", defs=[schema.def_record("function", "f", 1, 2)]),
        _record("dead.py", defs=[schema.def_record("function", "g", 1, 2)]),
        _record("main.py", has_main_guard=True,
                imports=[schema.import_record("used", kind="import"),
                         schema.import_record("used", kind="from",
                                              names=[{"name": "f", "alias": None}])],
                calls=[schema.call_record("f", None, 3)]),
    ]
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    assert report["schema"] == 1
    assert [f["path"] for f in report["files"]] == ["dead.py"]
    assert [(s["path"], s["name"]) for s in report["symbols"]] == [("dead.py", "g")]
