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
    assert report["schema"] == schema.SCHEMA_VERSION
    assert [_norm_path(f["path"]) for f in report["files"]] == ["truly_dead.py"]
    got = {(_norm_path(s["path"]), s["name"]) for s in report["symbols"]}
    assert got == {("utils.py", "stale"), ("pkg/core.py", "internal"),
                   ("truly_dead.py", "gone")}


def test_js_fixture_exact_ghost_set():
    report = _fixture_ghosts("js_app")
    assert report["schema"] == schema.SCHEMA_VERSION
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
    assert report["schema"] == schema.SCHEMA_VERSION
    assert [f["path"] for f in report["files"]] == ["dead.py"]
    assert [(s["path"], s["name"]) for s in report["symbols"]] == [("dead.py", "g")]

def test_resolve_python_tries_source_roots(tmp_path):
    """Day 7 dogfood: GhostCode flagged its own backend as dead.

    A backend/ source layout means `from api.app import x` resolves to
    backend/api/app.py, not repo-root api/app.py. Absolute imports are
    tried against the repo root first, then each source root.
    """
    (tmp_path / "backend" / "api").mkdir(parents=True)
    (tmp_path / "backend" / "api" / "__init__.py").write_text("")
    (tmp_path / "backend" / "api" / "app.py").write_text("")
    root = str(tmp_path)
    assert resolve_module(root, "x.py", "python", "api.app") == []
    assert resolve_module(root, "x.py", "python", "api.app",
                          ("backend",)) == ["backend/api/app.py"]
    assert resolve_module(root, "x.py", "python", "api",
                          ("backend",)) == ["backend/api/__init__.py"]
    assert resolve_module(root, "x.py", "python", "os",
                          ("backend",)) == []  # stdlib stays external


def test_src_layout_absolute_import_keeps_module_live(tmp_path):
    """End to end: a test importing through a backend/ layout keeps the
    module and the imported symbol live (no ghost flags)."""
    (tmp_path / "backend" / "api").mkdir(parents=True)
    (tmp_path / "backend" / "api" / "__init__.py").write_text("")
    (tmp_path / "backend" / "api" / "app.py").write_text(
        "def create_app():\n    return 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_api.py").write_text(
        "from api.app import create_app\n\n"
        "def test_x():\n    assert create_app() == 1\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    file_ghosts = {_norm_path(f["path"]) for f in report["files"]}
    assert "backend/api/app.py" not in file_ghosts
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("backend/api/app.py", "create_app") not in sym_ghosts


def test_from_import_of_submodule_links_the_file(tmp_path):
    """Day 7 dogfood: `from app.routers import analyze` imports the
    submodule file, not just the package. Without the file edge every
    FastAPI router looks dead."""
    (tmp_path / "backend" / "app" / "routers").mkdir(parents=True)
    (tmp_path / "backend" / "app" / "__init__.py").write_text("")
    (tmp_path / "backend" / "app" / "routers" / "__init__.py").write_text("")
    (tmp_path / "backend" / "app" / "routers" / "analyze.py").write_text(
        "def run():\n    return 1\n")
    (tmp_path / "backend" / "app" / "main.py").write_text(
        "from app.routers import analyze\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    file_ghosts = {_norm_path(f["path"]) for f in report["files"]}
    assert "backend/app/routers/analyze.py" not in file_ghosts


def test_relative_from_import_of_submodule_links_the_file(tmp_path):
    """`from . import pr_jobs` inside backend/api/app.py links
    backend/api/pr_jobs.py."""
    (tmp_path / "backend" / "api").mkdir(parents=True)
    (tmp_path / "backend" / "api" / "__init__.py").write_text("")
    (tmp_path / "backend" / "api" / "app.py").write_text(
        "from . import pr_jobs\n")
    (tmp_path / "backend" / "api" / "pr_jobs.py").write_text(
        "def run():\n    return 1\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    file_ghosts = {_norm_path(f["path"]) for f in report["files"]}
    assert "backend/api/pr_jobs.py" not in file_ghosts


def test_from_import_binds_submodule_for_attribute_calls(tmp_path):
    """Day 7 dogfood: `from . import schema` then `schema.def_record()`
    must resolve through the submodule file, not the package __init__."""
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "schema.py").write_text(
        "def def_record():\n    return 1\n")
    (tmp_path / "pkg" / "user.py").write_text(
        "from . import schema\nschema.def_record()\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("pkg/schema.py", "def_record") not in sym_ghosts


def test_framework_convention_files_are_entries(tmp_path):
    """Day 7 dogfood: Next.js router files, tooling configs, .d.ts files
    and conftest.py are framework/tooling entries, never ghosts."""
    (tmp_path / "app" / "api").mkdir(parents=True)
    (tmp_path / "app" / "page.tsx").write_text(
        "export default function Page() { return null; }")
    (tmp_path / "app" / "layout.tsx").write_text(
        "export default function Layout({c}) { return c; }")
    (tmp_path / "app" / "api" / "route.ts").write_text(
        "export function GET() {}")
    (tmp_path / "next.config.mjs").write_text("export default {};")
    (tmp_path / "tailwind.config.ts").write_text("export default {};")
    (tmp_path / "types.d.ts").write_text("declare module 'x';")
    (tmp_path / "conftest.py").write_text("import pytest\n")
    root = str(tmp_path)
    records = analyze(root)
    got = {_norm_path(p) for p in entry_files(records)}
    assert {"app/page.tsx", "app/layout.tsx", "app/api/route.ts",
            "next.config.mjs", "tailwind.config.ts", "types.d.ts",
            "conftest.py"} <= got


def test_framework_entry_rules_stay_tight(tmp_path):
    """The new entry rules must not swallow real ghosts."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "page.tsx").write_text(
        "export default function Page() { return null; }")
    (tmp_path / "dead.ts").write_text(
        "export function neverCalled() { return 1; }")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    file_ghosts = {_norm_path(f["path"]) for f in report["files"]}
    assert "app/page.tsx" not in file_ghosts
    assert "dead.ts" in file_ghosts


def test_decorated_functions_are_live(tmp_path):
    """Day 7 dogfood: FastAPI route handlers are registered by decorator
    (@app.get), never called by name. Any decorator keeps the def live:
    the runtime invokes or transforms it, so no static call edge can."""
    (tmp_path / "app.py").write_text(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "\n"
        "@app.get(\"/health\")\n"
        "def health():\n"
        "    return {\"ok\": True}\n"
        "\n"
        "def dead():\n"
        "    return 0\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("app.py", "health") not in sym_ghosts
    assert ("app.py", "dead") in sym_ghosts


def test_default_export_of_entry_file_is_live(tmp_path):
    """Day 7 dogfood: Next.js renders a page's default export; nothing
    imports it, but it is framework-invoked, not dead."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "page.tsx").write_text(
        "export default function Landing() { return null; }")
    (tmp_path / "app" / "dead.tsx").write_text(
        "export default function Dead() { return null; }")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("app/page.tsx", "Landing") not in sym_ghosts
    assert ("app/dead.tsx", "Dead") in sym_ghosts  # not an entry: still dead


def test_constructor_and_dts_symbols_are_live(tmp_path):
    """`constructor` is invoked by `new`, never called by name; `.d.ts`
    declarations are type-level and erased at compile time."""
    (tmp_path / "lib.ts").write_text(
        "export class Box {\n"
        "  constructor() {}\n"
        "  open() {}\n"
        "}\n"
        "new Box().open();\n")
    (tmp_path / "types.d.ts").write_text(
        "declare class Widget {\n"
        "  render(): void;\n"
        "}\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("lib.ts", "constructor") not in sym_ghosts
    assert ("lib.ts", "open") not in sym_ghosts
    assert ("types.d.ts", "Widget") not in sym_ghosts
    assert ("types.d.ts", "render") not in sym_ghosts


def test_resolve_js_at_alias(tmp_path):
    """Day 7 dogfood: the frontend imports everything via `@/`.

    `@/lib/format` mirrors the Next.js tsconfig default `@/* -> ./*`:
    resolve against the nearest ancestor directory of the importing file.
    """
    (tmp_path / "frontend" / "lib").mkdir(parents=True)
    (tmp_path / "frontend" / "lib" / "format.ts").write_text("")
    (tmp_path / "frontend" / "components").mkdir()
    root = str(tmp_path)
    assert resolve_module(root, "frontend/components/X.tsx", "typescript",
                          "@/lib/format") == ["frontend/lib/format.ts"]
    assert resolve_module(root, "frontend/components/X.tsx", "typescript",
                          "@/nope") == []
    assert resolve_module(root, "frontend/components/X.tsx", "typescript",
                          "react") == []  # bare stays external


def test_dynamic_import_uses_default_export(tmp_path):
    """Day 7 dogfood: `next/dynamic(() => import("./Canvas"))` renders
    the default export; the dynamic import keeps it live."""
    (tmp_path / "components").mkdir()
    (tmp_path / "components" / "Canvas.tsx").write_text(
        "export default function Canvas() { return null; }")
    (tmp_path / "view.tsx").write_text(
        "const Canvas = dynamic(() => import(\"./components/Canvas\"));\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("components/Canvas.tsx", "Canvas") not in sym_ghosts


def test_jsx_references_keep_symbols_live(tmp_path):
    """Day 7 dogfood: `<Progress/>` and `onSelect={onSelect}` in JSX are
    real references; components and handlers used only through JSX are
    not dead."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "page.tsx").write_text(
        "async function onSelect() {}\n"
        "function Progress() { return null; }\n"
        "function neverUsed() { return 1; }\n"
        "export default function Page() {\n"
        "  return <div onClick={onSelect}><Progress /></div>;\n"
        "}\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("app/page.tsx", "onSelect") not in sym_ghosts
    assert ("app/page.tsx", "Progress") not in sym_ghosts
    assert ("app/page.tsx", "Page") not in sym_ghosts
    assert ("app/page.tsx", "neverUsed") in sym_ghosts


def test_nested_jsx_expressions_keep_symbols_live(tmp_path):
    """`onClick={cond ? undefined : onRerun}`: references nested inside
    JSX expressions are still references."""
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "page.tsx").write_text(
        "function onRerun() {}\n"
        "function dead() {}\n"
        "export default function Page({cond}) {\n"
        "  return <button onClick={cond ? undefined : onRerun}>x</button>;\n"
        "}\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    report = detect_ghosts(records, graph)
    sym_ghosts = {(_norm_path(s["path"]), s["name"])
                  for s in report["symbols"]}
    assert ("app/page.tsx", "onRerun") not in sym_ghosts
    assert ("app/page.tsx", "dead") in sym_ghosts
