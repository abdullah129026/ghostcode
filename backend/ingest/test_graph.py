"""Day 2 graph tests: resolution, entry points, and ghost detection.

The fixture repos under fixtures/ are the money test: hand-built apps
with KNOWN ghost sets. Exact assertions, no maybes. See fixtures/README.md
for the rules each fixture pins down.
"""

import os

from ingest.resolve import import_edges, resolve_module

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
