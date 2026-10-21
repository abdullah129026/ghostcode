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
        has_main_guard = _py_main_guard(tree.root_node)
        default_export = None
    else:
        imports, defs, exports, calls, default_export = _extract_js(tree.root_node)
        has_main_guard = False
    loc = source.count(b"\n") + (0 if source.endswith(b"\n") else 1)
    return schema.file_record(path, language, loc, imports, defs, exports, calls,
                              has_main_guard=has_main_guard,
                              default_export=default_export)


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
            decorated = any(a.type == "decorated_definition"
                            for a in ancestors)
            defs.append(
                schema.def_record(kind, _text(name), _lineno(node),
                                   _end_lineno(node), parent,
                                   decorated=decorated)
            )
        elif node.type == "call":
            dynamic = _py_dynamic_import(node)
            if dynamic is not None:
                imports.append(dynamic)
            else:
                calls.append(_py_call(node))
        elif node.type == "return_statement":
            # `return _inner`: a returned name is used by the caller.
            for child in node.children:
                for ref in _py_arg_refs(child):
                    if "." in ref:
                        receiver, _, name = ref.rpartition(".")
                    else:
                        receiver, name = None, ref
                    calls.append(schema.call_record(name, receiver,
                                                    _lineno(child)))
        elif node.type == "type":
            # `def f(req: CodeRequest)`: names in type position are
            # references. Nested types (Optional[X]) arrive as their own
            # `type` nodes, so direct children suffice.
            for child in node.children:
                if child.type == "identifier":
                    calls.append(schema.call_record(_text(child), None,
                                                    _lineno(child)))
    return imports, defs, exports, calls


def _py_main_guard(root):
    """True when the file has an `if __name__ == "__main__":` block.

    Text match inside the if condition, not a full comparison parse:
    nobody writes `__name__` and `__main__` in one condition by accident.
    """
    for node, _ in _iter_nodes(root):
        if node.type != "if_statement":
            continue
        condition = node.child_by_field_name("condition")
        if condition is None:
            continue
        text = _text(condition)
        if "__name__" in text and "__main__" in text:
            return True
    return False


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
    return schema.call_record(name, receiver, _lineno(node),
                              args=_py_call_args(node))


def _py_call_args(node):
    """Name references in argument position (callbacks, Depends, thread
    targets). Nested calls are recorded as calls themselves; literals,
    splats and subscripts are not name references."""
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return []
    refs = []
    for child in arguments.children:
        refs.extend(_py_arg_refs(child))
    return refs


def _py_arg_refs(node):
    if node.type == "identifier":
        return [_text(node)]
    if node.type == "attribute":
        return [_py_dotted(node)]
    if node.type == "keyword_argument":
        value = node.child_by_field_name("value")
        return _py_arg_refs(value) if value is not None else []
    return []


def _py_dotted(node):
    obj = node.child_by_field_name("object")
    attr = node.child_by_field_name("attribute")
    if obj is None or attr is None:
        return _text(node)
    head = _py_dotted(obj) if obj.type == "attribute" else _text(obj)
    return head + "." + _text(attr)


_DYNAMIC_CALLS = {"importlib.import_module", "__import__"}


def _py_dynamic_import(node):
    """importlib.import_module("pkg.mod") with a literal: a real dependency.

    Only the literal-string case; anything computed stays invisible, and
    the file it would have pointed at keeps its ghost status. That is the
    documented ceiling: literal dynamic imports resolve, the rest do not.
    """
    func = node.child_by_field_name("function")
    if func is None or _text(func) not in _DYNAMIC_CALLS:
        return None
    args = node.child_by_field_name("arguments")
    if args is None:
        return None
    for arg in args.children:
        if arg.type == "string":
            return schema.import_record(_text(arg).strip("\"'"),
                                        lineno=_lineno(node), kind="dynamic")
    return None


# ---------------------------------------------------------------------------
# JavaScript / TypeScript (same node types, different parser per extension)
# ---------------------------------------------------------------------------

def _extract_js(root):
    imports, defs, exports, calls = [], [], [], []
    default_export = None
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
            names, default = _js_export_info(node)
            exports.extend(names)
            if default is not None:
                default_export = default
        elif node.type == "call_expression":
            record = _js_call(node, ancestors)
            if record is not None:
                kind, payload = record
                (imports if kind == "import" else calls).append(payload)
        elif node.type in ("jsx_opening_element", "jsx_self_closing_element"):
            # `<Progress/>` is a real reference to the component; lowercase
            # names are intrinsic elements (<div>), not references.
            name_node = next((c for c in node.children
                              if c.type in ("identifier", "jsx_identifier",
                                            "nested_identifier")), None)
            if name_node is not None:
                text = _text(name_node).split(".")[0]
                if text[:1].isupper():
                    calls.append(schema.call_record(text, None,
                                                    _lineno(name_node)))
        elif node.type == "jsx_expression":
            # `{onSelect}` and `{cond ? undefined : onRerun}`: identifiers
            # in JSX expressions are references. Recorded as calls so local
            # and imported names resolve through the usual machinery.
            for ref in _jsx_refs(node):
                calls.append(schema.call_record(ref, None, _lineno(node)))
        elif node.type == "assignment_expression":
            exports.extend(_js_cjs_export(node))
    return imports, defs, exports, calls, default_export


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


def _js_export_info(node):
    """export { a, b as c } / export function f() / export default ...

    Returns (names, default_name). `export { x as default }` counts as a
    default export too.
    """
    names, default = [], None
    is_default = re.match(r"\s*export\s+default\b", _text(node)) is not None
    for child in node.children:
        if child.type == "export_clause":
            for spec in child.children:
                if spec.type != "export_specifier":
                    continue
                name = spec.child_by_field_name("name")
                spec_alias = spec.child_by_field_name("alias")
                text = _text(name) if name is not None else ""
                alias = _text(spec_alias) if spec_alias is not None else None
                if not text:
                    continue
                names.append(text)
                if is_default or alias == "default":
                    default = text
        elif child.type in ("function_declaration", "generator_function_declaration",
                            "class_declaration"):
            name = child.child_by_field_name("name")
            if name is not None:
                names.append(_text(name))
                if is_default:
                    default = _text(name)
        elif child.type == "variable_declarator":
            name = child.child_by_field_name("name")
            if name is not None:
                names.append(_text(name))
                if is_default:
                    default = _text(name)
    return names, default


def _js_call(node, ancestors):
    """Returns ("call", record) or ("import", record) for require("x")."""
    func = node.child_by_field_name("function")
    if func is None:
        return None
    if func.type == "import":
        # dynamic import("./chunk.js"): same treatment as a static import
        # when the specifier is a literal, invisible otherwise
        args = node.child_by_field_name("arguments")
        if args is not None:
            for arg in args.children:
                if arg.type == "string":
                    return ("import", schema.import_record(
                        _text(arg).strip("\"'`"), lineno=_lineno(node),
                        kind="dynamic"))
        return None
    dotted = _text(func)
    if dotted == "require":
        args = node.child_by_field_name("arguments")
        if args is not None:
            for arg in args.children:
                if arg.type == "string":
                    return ("import", schema.import_record(
                        _text(arg).strip("\"'`"),
                        names=_js_require_names(ancestors),
                        lineno=_lineno(node), kind="require"))
        return None
    if "." in dotted:
        receiver, _, name = dotted.rpartition(".")
    else:
        receiver, name = None, dotted
    return ("call", schema.call_record(name, receiver, _lineno(node),
                                       args=_js_call_args(node)))


def _js_call_args(node):
    """Name references in argument position, mirroring _py_call_args."""
    arguments = node.child_by_field_name("arguments")
    if arguments is None:
        return []
    refs = []
    for child in arguments.children:
        refs.extend(_js_arg_refs(child))
    return refs


def _js_arg_refs(node):
    if node.type == "identifier":
        return [_text(node)]
    if node.type == "member_expression":
        return [_js_dotted(node)]
    return []


def _js_dotted(node):
    obj = node.child_by_field_name("object")
    prop = node.child_by_field_name("property")
    if obj is None or prop is None:
        return _text(node)
    head = _js_dotted(obj) if obj.type == "member_expression" else _text(obj)
    return head + "." + _text(prop)


def _jsx_refs(node):
    """Identifier references inside a JSX expression.

    Nested calls are skipped (their function and arguments are recorded
    separately); member expressions contribute their base object.
    """
    refs = []
    for child in node.children:
        if child.type == "call_expression":
            continue
        if child.type == "identifier":
            refs.append(_text(child))
        elif child.type == "member_expression":
            refs.append(_js_dotted(child).split(".")[0])
        else:
            refs.extend(_jsx_refs(child))
    return refs


def _js_require_names(ancestors):
    """Names bound by `const { a, b: c } = require("./m")`.

    Without these, every destructured require() looks like a bare module
    load and the used names never resolve. `const x = require("./m")`
    (no destructuring) binds nothing here; call resolution handles the
    `x.name()` shape through the namespace instead.
    """
    if not ancestors:
        return []
    parent = ancestors[-1]
    if parent.type != "variable_declarator":
        return []
    name = parent.child_by_field_name("name")
    if name is None or name.type != "object_pattern":
        return []
    bound = []
    for child in name.children:
        if child.type in ("shorthand_property_identifier",
                          "shorthand_property_identifier_pattern"):
            bound.append({"name": _text(child), "alias": None})
        elif child.type in ("pair", "pair_pattern"):
            key = child.child_by_field_name("key")
            value = child.child_by_field_name("value")
            if key is not None:
                bound.append({
                    "name": _text(key),
                    "alias": _text(value) if value is not None and "identifier" in value.type else None,
                })
    return bound


def _js_cjs_export(node):
    """Names exposed through CommonJS: a list, possibly empty.

    `module.exports = { parse, stringify }` exposes both keys;
    `module.exports = something` exposes an unknowable shape, so it
    reports nothing (the file-level edge from require() still exists).
    """
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    if left is None or left.type != "member_expression":
        return []
    dotted = _text(left)
    if dotted == "module.exports":
        if right is not None and right.type == "object":
            names = []
            for child in right.children:
                if child.type == "shorthand_property_identifier":
                    names.append(_text(child))
                elif child.type == "pair":
                    key = child.child_by_field_name("key")
                    if key is not None:
                        names.append(_text(key).strip("\"'`"))
            return names
        return []
    for prefix in ("module.exports.", "exports."):
        if dotted.startswith(prefix):
            return [dotted[len(prefix):]]
    return []
