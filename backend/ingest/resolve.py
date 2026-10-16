"""Resolve import specifiers and call sites to concrete graph edges.

Day 1 records what each file imports and calls. This module answers the
next question: which repo file does `./lib.js` or `.utils` point at, and
which defined symbol does `used()` refer to?

Rule of thumb throughout: when resolution is ambiguous, keep the node
live. A missed ghost is a shrug; a ghost that was actually live kills
trust in the whole report.
"""

import os

_JS_EXTENSIONS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts")


def _isfile(root, relpath):
    return os.path.isfile(os.path.join(root, relpath))


def _norm(relpath):
    return os.path.normpath(relpath)


def resolve_module(root, from_path, language, specifier):
    """Repo-relative paths a module specifier could point at (maybe none).

    Unresolvable specifiers (stdlib, node_modules, typos) return [] and
    stay external module nodes on the graph.
    """
    if not specifier:
        return []
    if language == "python":
        return _resolve_python(root, from_path, specifier)
    return _resolve_js(root, from_path, specifier)


def _resolve_python(root, from_path, specifier):
    level = len(specifier) - len(specifier.lstrip("."))
    rest = specifier[level:]
    if level:
        base = os.path.dirname(from_path)
        for _ in range(level - 1):
            base = os.path.dirname(base)
        parts = rest.split(".") if rest else []
    else:
        base, parts = "", specifier.split(".")
    target = _norm(os.path.join(base, *parts)) if parts else _norm(base)
    found = []
    for candidate in (target + ".py", os.path.join(target, "__init__.py")):
        if _isfile(root, candidate):
            found.append(_norm(candidate))
    return found


def _resolve_js(root, from_path, specifier):
    if not specifier.startswith("."):
        return []  # bare specifier: node_modules or a builtin, external
    base = _norm(os.path.join(os.path.dirname(from_path), specifier))
    if _isfile(root, base):
        return [base]
    found = []
    for ext in _JS_EXTENSIONS:
        if _isfile(root, base + ext):
            found.append(_norm(base + ext))
    for ext in _JS_EXTENSIONS:
        index = os.path.join(base, "index" + ext)
        if _isfile(root, index):
            found.append(_norm(index))
    return found


def import_edges(root, records):
    """(src_path, dst_path, kind) file -> file edges for resolved imports."""
    edges, seen = [], set()
    for record in records:
        for imp in record["imports"]:
            targets = resolve_module(root, record["path"],
                                     record["language"], imp["module"])
            for target in targets:
                _add_file_edge(edges, seen, record["path"], target, imp["kind"])
                if record["language"] == "python":
                    for parent in _parent_packages(root, target):
                        _add_file_edge(edges, seen, record["path"],
                                       parent, "package")
    return edges


def _add_file_edge(edges, seen, src, dst, kind):
    key = (src, dst, kind)
    if key not in seen and src != dst:
        seen.add(key)
        edges.append((src, dst, kind))


def _parent_packages(root, target):
    """__init__.py files executed when importing a submodule.

    `import pkg.mod` runs `pkg/__init__.py` first, so the package surface
    is never a ghost just because everyone imports through it.
    """
    out = []
    directory = os.path.dirname(target)
    while directory:
        init = _norm(os.path.join(directory, "__init__.py"))
        if _isfile(root, init):
            out.append(init)
        directory = os.path.dirname(directory)
    return out
