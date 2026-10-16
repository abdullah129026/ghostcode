# Ghost fixtures

Two tiny apps with KNOWN ghost sets. `test_graph.py` asserts the exact
sets end to end (`analyze` -> `build_graph` -> `add_resolved_edges` ->
`detect_ghosts`). If you change resolution or entry rules, these tests
tell you what moved. A false positive here is the most embarrassing
failure this project can have, so the fixtures pin the judgment calls:

## Rules pinned by py_app

- `main.py` is an entry point because of its `__main__` guard, not
  because something imports it.
- `utils.stale` is a ghost: defined, never called, never imported.
- `dead.forgotten` is NOT a ghost: `main.py` does
  `from dead import forgotten` and never calls it, but an imported name
  counts as used. Deleting it means touching the importer, so it is
  never a safe auto-delete. Unused-import linting is a different tool.
- `truly_dead.py` is a file ghost (nothing imports it) and `gone` is a
  symbol ghost.
- `pkg/__init__.py` re-exports `api` from `.core`: the re-export chain
  resolves, so `pkg.core.api` is live (called from `main.py`) while
  `pkg.core.internal` is a ghost.
- Importing `pkg.mod` also links `pkg/__init__.py` (importing a
  submodule executes the package), so barrel files are never ghosts.

Expected: files = {`truly_dead.py`};
symbols = {`utils.py::stale`, `pkg/core.py::internal`, `truly_dead.py::gone`}.

## Rules pinned by js_app

- `index.js` is an entry point by the root-index convention.
- `lib.unused` is a ghost: exported but never called. Exported does not
  mean live; v1 is app-oriented.
- `lib.test.js` is an entry point (test file); its `test()` calls do not
  need resolution.
- `view.js`'s default-exported `render` resolves through
  `import render from "./view.js"`.
- `cjs.js` pins CommonJS interop: `const { parse } = require("./cjs.js")`
  keeps `parse` live; `stringify` (in `module.exports = {...}` but never
  required by name) is a ghost.
- `lazy.js` has no static importers but is loaded via dynamic
  `import("./lazy.js")` with a literal specifier, so it stays live.
- `orphan.js` is a file ghost and `lost` is a symbol ghost.

Expected: files = {`orphan.js`};
symbols = {`lib.js::unused`, `cjs.js::stringify`, `orphan.js::lost`}.
