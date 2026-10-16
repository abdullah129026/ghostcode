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


# ---------------------------------------------------------------------------
# Symbol resolution: which defined symbol does a call or import name refer to
# ---------------------------------------------------------------------------

def _records_by_path(records):
    return {r["path"]: r for r in records}


def _resolve_name(root, by_path, path, name, seen):
    """Chase a name to (path, kind, name), following barrel re-exports.

    `from pkg import api` where `pkg/__init__.py` does `from .core import
    api` resolves to the def in `pkg/core.py`, not to the __init__ file.
    """
    if (path, name) in seen:
        return None
    seen = seen | {(path, name)}
    record = by_path.get(path)
    if record is None:
        return None
    for d in record["defs"]:
        if d["name"] == name:
            return (path, d["kind"], name)
    for imp in record["imports"]:
        if imp["kind"] not in ("from", "require"):
            continue
        if name not in {n["name"] for n in imp.get("names", [])}:
            continue
        for target in resolve_module(root, path, record["language"], imp["module"]):
            hit = _resolve_name(root, by_path, target, name, seen)
            if hit is not None:
                return hit
    return None


def _resolve_default(root, by_path, target):
    """(path, kind, name) for a default import, or [] when unknowable."""
    record = by_path.get(target)
    if record is None:
        return []
    name = record.get("default_export")
    if not name:
        return []
    return [(target, d["kind"], name) for d in record["defs"]
            if d["name"] == name]


def _import_bindings(root, record):
    """Local names bound by imports: (named, default, namespace) maps.

    named:     local -> (target_path, exported_name), e.g. `from m import f`
    default:   local -> target_path, e.g. `import render from "./view.js"`
    namespace: local -> target_path, e.g. `import os`, `import * as ns`
    """
    named, default, namespace = {}, {}, {}
    for imp in record["imports"]:
        targets = resolve_module(root, record["path"],
                                 record["language"], imp["module"])
        if not targets:
            continue
        target = targets[0]
        if imp.get("default"):
            default[imp["default"]] = target
        for n in imp.get("names", []):
            local = n.get("alias") or n["name"]
            if local:
                named[local] = (target, n["name"])
        if imp.get("alias") and not imp.get("names") and not imp.get("default"):
            namespace[imp["alias"]] = target  # import * as ns / import x as y
        elif imp["kind"] == "import" and not imp.get("names"):
            local = imp.get("alias") or imp["module"].split(".")[0]
            namespace.setdefault(local, target)  # `import os`
    return named, default, namespace


def call_edges(root, records):
    """(src, dst_path, dst_kind, dst_name, "call") for resolved call sites."""
    edges, seen = [], set()
    by_path = _records_by_path(records)
    for record in records:
        named, default, namespace = _import_bindings(root, record)
        local_defs = {}
        for d in record["defs"]:
            local_defs.setdefault(d["name"], []).append(d["kind"])
        for call in record["calls"]:
            name, receiver = call["name"], call["receiver"]
            if not name:
                continue
            hits = _resolve_call(root, by_path, record, named, default,
                                 namespace, local_defs, name, receiver)
            for hit in hits:
                key = (record["path"],) + hit + ("call",)
                if key not in seen:
                    seen.add(key)
                    edges.append((record["path"],) + hit + ("call",))
    return edges


def _resolve_call(root, by_path, record, named, default, namespace,
                  local_defs, name, receiver):
    if receiver is None:
        if name in local_defs:
            return [(record["path"], kind, name) for kind in local_defs[name]]
        if name in named:
            target, exported = named[name]
            hit = _resolve_name(root, by_path, target, exported, set())
            return [hit] if hit else []
        if name in default:
            return _resolve_default(root, by_path, default[name])
        return []
    methods = [kind for kind in local_defs.get(name, []) if kind == "method"]
    if methods:
        # The receiver's type is unknowable statically, so any same-file
        # method with this name keeps it live. False negatives beat
        # false positives: a missed ghost is a shrug, a live method
        # flagged as dead kills trust.
        return [(record["path"], "method", name)]
    base = receiver.split(".")[0]
    if base in namespace:
        hit = _resolve_name(root, by_path, namespace[base], name, set())
        return [hit] if hit else []
    if base in named:
        # `from m import obj` then `obj.method()`: obj names a module here
        # often enough (from pkg import submodule) to be worth the chase
        hit = _resolve_name(root, by_path, named[base][0], name, set())
        return [hit] if hit else []
    return []


def use_edges(root, records):
    """(src, dst_path, dst_kind, dst_name, "uses") for named imports.

    An imported name counts as used: deleting it means touching the
    importer too, so it is never a safe auto-delete. Unused-import
    linting is a different tool's job.
    """
    edges, seen = [], set()
    by_path = _records_by_path(records)
    for record in records:
        named, default, _namespace = _import_bindings(root, record)
        for _local, (target, exported) in named.items():
            hit = _resolve_name(root, by_path, target, exported, set())
            if hit:
                _add_sym_edge(edges, seen, record["path"], hit, "uses")
        for _local, target in default.items():
            for hit in _resolve_default(root, by_path, target):
                _add_sym_edge(edges, seen, record["path"], hit, "uses")
    return edges


def _add_sym_edge(edges, seen, src, hit, kind):
    key = (src,) + hit + (kind,)
    if key not in seen:
        seen.add(key)
        edges.append((src,) + hit + (kind,))
