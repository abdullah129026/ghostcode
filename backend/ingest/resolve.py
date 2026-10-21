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


def _source_roots(records):
    """Top-level dirs that hold Python modules, e.g. backend/ in a
    backend/ layout or src/ in a src layout.

    Derived from the records, not the filesystem: a source root is any
    first path component of a parsed .py file below the repo root. Only
    consulted when an absolute import fails at the repo root, so flat
    layouts behave exactly as before.
    """
    roots = set()
    for record in records:
        if not record["path"].endswith(".py"):
            continue
        head, sep, _ = record["path"].partition("/")
        if sep:
            roots.add(head)
    return sorted(roots)


def resolve_module(root, from_path, language, specifier, source_roots=()):
    """Repo-relative paths a module specifier could point at (maybe none).

    Unresolvable specifiers (stdlib, node_modules, typos) return [] and
    stay external module nodes on the graph.
    """
    if not specifier:
        return []
    if language == "python":
        return _resolve_python(root, from_path, specifier, source_roots)
    return _resolve_js(root, from_path, specifier)


def _resolve_python(root, from_path, specifier, source_roots):
    level = len(specifier) - len(specifier.lstrip("."))
    rest = specifier[level:]
    if level:
        base = os.path.dirname(from_path)
        for _ in range(level - 1):
            base = os.path.dirname(base)
        parts = rest.split(".") if rest else []
        bases = (base,)
    else:
        parts = specifier.split(".")
        # Repo root first, then source roots: every hit is an edge, and
        # ambiguous hits keep nodes live rather than flagging them.
        bases = ("",) + tuple(source_roots)
    found = []
    for base in bases:
        target = _norm(os.path.join(base, *parts)) if parts else _norm(base)
        for candidate in (target + ".py", os.path.join(target, "__init__.py")):
            candidate = _norm(candidate)
            if candidate not in found and _isfile(root, candidate):
                found.append(candidate)
    return found


def _resolve_js(root, from_path, specifier):
    if specifier.startswith("@/"):
        return _resolve_at_alias(root, from_path, specifier[2:])
    if not specifier.startswith("."):
        return []  # bare specifier: node_modules or a builtin, external
    base = _norm(os.path.join(os.path.dirname(from_path), specifier))
    return _probe_js_base(root, base)


def _probe_js_base(root, base):
    """All files a JS base path could point at (maybe none)."""
    if _isfile(root, base):
        return [base]
    found = []
    for ext in _JS_EXTENSIONS:
        if _isfile(root, base + ext):
            found.append(_norm(base + ext))
    for ext in _JS_EXTENSIONS:
        index = _norm(os.path.join(base, "index" + ext))
        if _isfile(root, index):
            found.append(index)
    return found


def _resolve_at_alias(root, from_path, rest):
    """Resolve a `@/` path alias (the Next.js/Vite `@/* -> ./*` default).

    Tries the importing file's ancestor directories nearest-first, so
    `@/lib/format` from `frontend/components/X.tsx` lands on
    `frontend/lib/format.ts` without parsing tsconfig files.
    """
    # ponytail: ancestor walk instead of parsing compilerOptions.paths;
    # only the `@/* -> ./*` default mapping is honored. Parse tsconfig
    # paths if a repo ever needs a custom alias.
    directory = os.path.dirname(from_path)
    while True:
        hit = _probe_js_base(root, _norm(os.path.join(directory, rest)))
        if hit:
            return hit
        parent = os.path.dirname(directory)
        if parent == directory:
            return []
        directory = parent


def import_edges(root, records):
    """(src_path, dst_path, kind) file -> file edges for resolved imports."""
    edges, seen = [], set()
    source_roots = _source_roots(records)
    for record in records:
        for imp in record["imports"]:
            targets = resolve_module(root, record["path"],
                                     record["language"], imp["module"],
                                     source_roots)
            for target in targets:
                _add_file_edge(edges, seen, record["path"], target, imp["kind"])
                if record["language"] == "python":
                    for parent in _parent_packages(root, target):
                        _add_file_edge(edges, seen, record["path"],
                                       parent, "package")
            if record["language"] == "python" and imp["kind"] == "from":
                names = [n["name"] for n in imp.get("names", [])]
                for target in _submodule_targets(root, record, imp["module"],
                                                 names, source_roots):
                    _add_file_edge(edges, seen, record["path"], target,
                                   "from-submodule")
                    for parent in _parent_packages(root, target):
                        _add_file_edge(edges, seen, record["path"],
                                       parent, "package")
    return edges


def _submodule_targets(root, record, module, names, source_roots):
    """Repo-relative files for submodule names in a from-import.

    `from pkg import sub` links pkg/sub.py when it exists. When it does
    not, the caller falls back to the package: the name may be a
    re-exported symbol instead (`from pkg import api`).
    """
    dots = len(module) - len(module.lstrip("."))
    rest = module[dots:]
    prefix = "." * dots + (rest + "." if rest else "")
    found = []
    for name in names:
        for target in resolve_module(root, record["path"], "python",
                                     prefix + name, source_roots):
            if target not in found:
                found.append(target)
    return found


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


def _resolve_name(root, by_path, path, name, seen, source_roots=()):
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
        for target in resolve_module(root, path, record["language"],
                                     imp["module"], source_roots):
            hit = _resolve_name(root, by_path, target, name, seen,
                                source_roots)
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


def _import_bindings(root, record, source_roots=()):
    """Local names bound by imports: (named, default, namespace) maps.

    named:     local -> (target_path, exported_name), e.g. `from m import f`
    default:   local -> target_path, e.g. `import render from "./view.js"`
    namespace: local -> target_path, e.g. `import os`, `import * as ns`
    """
    named, default, namespace = {}, {}, {}
    for imp in record["imports"]:
        targets = resolve_module(root, record["path"],
                                 record["language"], imp["module"],
                                 source_roots)
        if not targets:
            continue
        target = targets[0]
        if imp.get("default"):
            default[imp["default"]] = target
        for n in imp.get("names", []):
            local = n.get("alias") or n["name"]
            if not local:
                continue
            bound = target
            if record["language"] == "python" and imp["kind"] == "from":
                subs = _submodule_targets(root, record, imp["module"],
                                          [n["name"]], source_roots)
                if subs:
                    # `from pkg import submod`: the local name IS the
                    # submodule, so `schema.def_record()` resolves through
                    # the submodule file, not the package __init__.
                    bound = subs[0]
            named[local] = (bound, n["name"])
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
    source_roots = _source_roots(records)
    for record in records:
        named, default, namespace = _import_bindings(root, record,
                                                     source_roots)
        local_defs = {}
        for d in record["defs"]:
            local_defs.setdefault(d["name"], []).append(d["kind"])
        for call in record["calls"]:
            name, receiver = call["name"], call["receiver"]
            if not name:
                continue
            hits = _resolve_call(root, by_path, record, named, default,
                                 namespace, local_defs, name, receiver,
                                 source_roots)
            for hit in hits:
                key = (record["path"],) + hit + ("call",)
                if key not in seen:
                    seen.add(key)
                    edges.append((record["path"],) + hit + ("call",))
            for arg in call.get("args", ()):
                for hit in _resolve_arg(root, by_path, record, named,
                                        default, namespace, local_defs, arg,
                                        source_roots):
                    key = (record["path"],) + hit + ("uses",)
                    if key not in seen:
                        seen.add(key)
                        edges.append((record["path"],) + hit + ("uses",))
    return edges


def _resolve_arg(root, by_path, record, named, default, namespace,
                 local_defs, arg, source_roots):
    """A name referenced in argument position is used: resolve it like a
    call target and return the hit, so callbacks and dependency-injected
    functions never look dead."""
    if "." not in arg:
        if arg in local_defs:
            return [(record["path"], kind, arg) for kind in local_defs[arg]]
        if arg in named:
            target, exported = named[arg]
            hit = _resolve_name(root, by_path, target, exported, set(),
                                source_roots)
            return [hit] if hit else []
        if arg in default:
            return _resolve_default(root, by_path, default[arg])
        return []
    base, _, attr = arg.partition(".")
    target = None
    if base in namespace:
        target = namespace[base]
    elif base in named:
        target = named[base][0]
    if target is None:
        return []
    hit = _resolve_name(root, by_path, target, attr.partition(".")[0],
                        set(), source_roots)
    return [hit] if hit else []


def _resolve_call(root, by_path, record, named, default, namespace,
                  local_defs, name, receiver, source_roots=()):
    if receiver is None:
        if name in local_defs:
            return [(record["path"], kind, name) for kind in local_defs[name]]
        if name in named:
            target, exported = named[name]
            hit = _resolve_name(root, by_path, target, exported, set(),
                                source_roots)
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
        hit = _resolve_name(root, by_path, namespace[base], name, set(),
                            source_roots)
        return [hit] if hit else []
    if base in named:
        # `from m import obj` then `obj.method()`: obj names a module here
        # often enough (from pkg import submodule) to be worth the chase
        hit = _resolve_name(root, by_path, named[base][0], name, set(),
                            source_roots)
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
    source_roots = _source_roots(records)
    for record in records:
        named, default, _namespace = _import_bindings(root, record,
                                                      source_roots)
        for _local, (target, exported) in named.items():
            hit = _resolve_name(root, by_path, target, exported, set(),
                                source_roots)
            if hit:
                _add_sym_edge(edges, seen, record["path"], hit, "uses")
        for _local, target in default.items():
            for hit in _resolve_default(root, by_path, target):
                _add_sym_edge(edges, seen, record["path"], hit, "uses")
        for imp in record["imports"]:
            if imp["kind"] != "dynamic":
                continue
            # `import("./chunk")` (e.g. next/dynamic) renders the target's
            # default export. Without this every lazily-loaded component
            # looks dead.
            targets = resolve_module(root, record["path"],
                                     record["language"], imp["module"],
                                     source_roots)
            for target in targets:
                for hit in _resolve_default(root, by_path, target):
                    _add_sym_edge(edges, seen, record["path"], hit, "uses")
    return edges


def _add_sym_edge(edges, seen, src, hit, kind):
    key = (src,) + hit + (kind,)
    if key not in seen:
        seen.add(key)
        edges.append((src,) + hit + (kind,))
