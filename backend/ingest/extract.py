"""Tree-sitter symbol extraction for Python, JavaScript, and TypeScript.

Each extractor walks the parse tree once and records:
  imports: module specifiers plus the names pulled from them
  defs:    functions, classes, and methods with line spans
  exports: names a module makes available to importers
  calls:   call sites with the callee name (edges resolved later by graph/)

tree-sitter finds the statement boundaries; the small text parsing inside an
already-located statement is stdlib work, not a second parser.
"""

import re

from tree_sitter import Language, Parser

import tree_sitter_javascript
import tree_sitter_python
import tree_sitter_typescript

from . import schema

_PY = Language(tree_sitter_python.language())
_JS = Language(tree_sitter_javascript.language())
_TS = Language(tree_sitter_typescript.language_typescript())
_TSX = Language(tree_sitter_typescript.language_tsx())

_PARSERS = {
    "python": Parser(_PY),
    "javascript": Parser(_JS),
    "typescript": Parser(_TS),
    "tsx": Parser(_TSX),
}

_EXTENSIONS = {
    "py": "python",
    "js": "javascript",
    "jsx": "javascript",
    "mjs": "javascript",
    "cjs": "javascript",
    "ts": "typescript",
    "tsx": "tsx",
    "mts": "typescript",
    "cts": "typescript",
}


def detect_language(filename):
    """Map a filename to a supported language, or None."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXTENSIONS.get(ext)


def _text(node):
    return node.text.decode("utf8", "replace")


def _lineno(node):
    return node.start_point[0] + 1


def _end_lineno(node):
    return node.end_point[0] + 1


def _iter_nodes(root):
    """Yield (node, ancestors) depth-first; ancestors is a tuple of parents."""
    stack = [(root, ())]
    while stack:
        node, ancestors = stack.pop()
        yield node, ancestors
        for child in reversed(node.children):
            stack.append((child, ancestors + (node,)))


def _enclosing_class(ancestors):
    for node in reversed(ancestors):
        if node.type in ("class_definition", "class_declaration"):
            name = node.child_by_field_name("name")
            return _text(name) if name is not None else None
    return None


def extract_file(path, source):
    """Parse one file's bytes, return a schema.file_record dict.

    Raises ValueError for unsupported languages, SyntaxError is never raised:
    tree-sitter parses partial/broken files and we record what it found.
    """
    language = detect_language(path)
    if language is None:
        raise ValueError(f"unsupported file type: {path}")
    tree = _PARSERS[language].parse(source)
    if language == "python":
        imports, defs, exports, calls = _extract_python(tree.root_node)
    else:
        imports, defs, exports, calls = _extract_js(tree.root_node)
    loc = source.count(b"\n") + (0 if source.endswith(b"\n") else 1)
    return schema.file_record(path, language, loc, imports, defs, exports, calls)


# ---------------------------------------------------------------------------
# Python
# ---------------------------------------------------------------------------

_FROM_RE = re.compile(r"from\s+([\w.]+)\s+import\s+(.+)")


def _extract_python(root):
    imports, defs, exports, calls = [], [], [], []
    for node, ancestors in _iter_nodes(root):
        if node.type == "import_statement":
            imports.extend(_py_plain_imports(node))
        elif node.type == "import_from_statement":
            imports.append(_py_from_import(node))
        elif node.type in ("function_definition", "class_definition"):
            name = node.child_by_field_name("name")
            if name is None:
                continue
            kind = "function" if node.type == "function_definition" else "class"
            parent = _enclosing_class(ancestors)
            if kind == "function" and parent:
                kind = "method"
            defs.append(
                schema.def_record(kind, _text(name), _lineno(node),
                                   _end_lineno(node), parent)
            )
        elif node.type == "call":
            calls.append(_py_call(node))
    return imports, defs, exports, calls


def _py_plain_imports(node):
    """import os, sys as system -> one record per module."""
    body = " ".join(_text(node).split())
    body = body[len("import "):]
    records = []
    for part in body.split(","):
        part = part.strip()
        name, _, alias = part.partition(" as ")
        records.append(schema.import_record(name.strip(), alias=(alias.strip() or None),
                                            lineno=_lineno(node)))
    return records


def _py_from_import(node):
    body = " ".join(_text(node).split())
    match = _FROM_RE.match(body)
    if not match:
        return schema.import_record(body, lineno=_lineno(node))
    module, names = match.group(1), match.group(2).strip("() ")
    parsed = []
    for part in names.split(","):
        part = part.strip()
        if not part or part == "*":
            continue
        name, _, alias = part.partition(" as ")
        parsed.append({"name": name.strip(), "alias": alias.strip() or None})
    return schema.import_record(module, names=parsed, lineno=_lineno(node), kind="from")


def _py_call(node):
    func = node.child_by_field_name("function")
    if func is None:
        return schema.call_record("", None, _lineno(node))
    dotted = _text(func)
    if "." in dotted:
        receiver, _, name = dotted.rpartition(".")
    else:
        receiver, name = None, dotted
    return schema.call_record(name, receiver, _lineno(node))


# ---------------------------------------------------------------------------
# JavaScript / TypeScript (same node types, different parser per extension)
# ---------------------------------------------------------------------------

def _extract_js(root):
    imports, defs, exports, calls = [], [], [], []
    for node, ancestors in _iter_nodes(root):
        if node.type == "import_statement":
            imports.append(_js_import(node))
        elif node.type in ("function_declaration", "generator_function_declaration",
                           "class_declaration"):
            name = node.child_by_field_name("name")
            if name is None:
                continue
            kind = "class" if "class" in node.type else "function"
            parent = _enclosing_class(ancestors)
            if kind == "function" and parent:
                kind = "method"
            defs.append(schema.def_record(kind, _text(name), _lineno(node),
                                          _end_lineno(node), parent))
        elif node.type == "method_definition":
            name = node.child_by_field_name("name")
            if name is not None:
                defs.append(schema.def_record("method", _text(name), _lineno(node),
                                              _end_lineno(node),
                                              _enclosing_class(ancestors)))
        elif node.type == "variable_declarator":
            record = _js_var_function(node)
            if record is not None:
                defs.append(record)
        elif node.type == "export_statement":
            exports.extend(_js_exports(node))
        elif node.type == "call_expression":
            record = _js_call(node)
            if record is not None:
                kind, payload = record
                (imports if kind == "import" else calls).append(payload)
        elif node.type == "assignment_expression":
            record = _js_cjs_export(node)
            if record is not None:
                exports.append(record)
    return imports, defs, exports, calls


def _js_import(node):
    source = next((c for c in node.children if c.type == "string"), None)
    module = _text(source).strip("\"'`") if source is not None else ""
    names, alias, default = [], None, None
    clause = next((c for c in node.children if c.type == "import_clause"), None)
    if clause is not None:
        for child in clause.children:
            if child.type == "identifier":
                default = _text(child)
            elif child.type == "namespace_import":
                alias = _text(child).split()[-1]
            elif child.type == "named_imports":
                for spec in child.children:
                    if spec.type != "import_specifier":
                        continue
                    name = spec.child_by_field_name("name")
                    spec_alias = spec.child_by_field_name("alias")
                    names.append({
                        "name": _text(name) if name is not None else "",
                        "alias": _text(spec_alias) if spec_alias is not None else None,
                    })
    record = schema.import_record(module, names=names, alias=alias,
                                  lineno=_lineno(node), kind="from")
    if default:
        record["default"] = default
    return record


def _js_var_function(node):
    """const f = () => {} / function f() {} assigned to a variable."""
    value = node.child_by_field_name("value")
    if value is None or value.type not in ("arrow_function", "function_expression",
                                           "generator_function"):
        return None
    name = node.child_by_field_name("name")
    if name is None:
        return None
    return schema.def_record("function", _text(name), _lineno(node),
                             _end_lineno(node))


def _js_exports(node):
    """export { a, b as c } / export function f() / export default ..."""
    found = []
    for child in node.children:
        if child.type == "export_clause":
            for spec in child.children:
                if spec.type != "export_specifier":
                    continue
                name = spec.child_by_field_name("name")
                found.append(_text(name) if name is not None else "")
        elif child.type in ("function_declaration", "generator_function_declaration",
                            "class_declaration"):
            name = child.child_by_field_name("name")
            if name is not None:
                found.append(_text(name))
        elif child.type == "variable_declarator":
            name = child.child_by_field_name("name")
            if name is not None:
                found.append(_text(name))
    return found


def _js_call(node):
    """Returns ("call", record) or ("import", record) for require("x")."""
    func = node.child_by_field_name("function")
    if func is None:
        return None
    dotted = _text(func)
    if dotted == "require":
        args = node.child_by_field_name("arguments")
        if args is not None:
            for arg in args.children:
                if arg.type == "string":
                    return ("import", schema.import_record(
                        _text(arg).strip("\"'`"), lineno=_lineno(node), kind="require"))
        return None
    if "." in dotted:
        receiver, _, name = dotted.rpartition(".")
    else:
        receiver, name = None, dotted
    return ("call", schema.call_record(name, receiver, _lineno(node)))


def _js_cjs_export(node):
    """module.exports = {...} / module.exports.x = ... / exports.x = ..."""
    left = node.child_by_field_name("left")
    if left is None or left.type != "member_expression":
        return None
    dotted = _text(left)
    if dotted == "module.exports":
        return "__module__"
    for prefix in ("module.exports.", "exports."):
        if dotted.startswith(prefix):
            return dotted[len(prefix):]
    return None
