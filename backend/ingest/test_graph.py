"""Day 2 graph tests: resolution, entry points, and ghost detection.

The fixture repos under fixtures/ are the money test: hand-built apps
with KNOWN ghost sets. Exact assertions, no maybes. See fixtures/README.md
for the rules each fixture pins down.
"""

import os

from ingest import schema
from ingest.resolve import call_edges, import_edges, resolve_module, use_edges

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


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
