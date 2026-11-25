"""Extractor fixtures: hand-written snippets with known symbols.

These pin the parser contract. A false negative here means the graph is
built on lies, so keep the fixtures small and the assertions exact.
"""

from ingest.extract import extract_file

import pytest


PY_FIXTURE = b'''\
import os
import sys as system
from .utils import helper as h, other

def top_function():
    helper()

class Widget:
    def render(self):
        top_function()

async def fetch_data():
    pass
'''

JS_FIXTURE = b'''\
import React, { useState } from "react";
import * as path from "path";
const fs = require("fs");

export function build() {
  return useState(null);
}

export default class App {
  handleClick() {
    build();
  }
}

const handler = () => build();
module.exports.extra = handler;
'''


def _defs(record):
    return {(d["kind"], d["name"]): d for d in record["defs"]}


def test_python_defs():
    defs = _defs(extract_file("a.py", PY_FIXTURE))
    assert ("function", "top_function") in defs
    assert ("class", "Widget") in defs
    assert ("method", "render") in defs
    assert defs[("method", "render")]["parent"] == "Widget"
    assert ("function", "fetch_data") in defs


def test_python_imports():
    record = extract_file("a.py", PY_FIXTURE)
    by_module = {i["module"]: i for i in record["imports"]}
    assert by_module["os"]["kind"] == "import"
    assert by_module["sys"]["alias"] == "system"
    assert by_module[".utils"]["kind"] == "from"
    assert {"name": "helper", "alias": "h"} in by_module[".utils"]["names"]


def test_python_calls():
    calls = {(c["name"], c["receiver"]) for c in extract_file("a.py", PY_FIXTURE)["calls"]}
    assert ("helper", None) in calls
    assert ("top_function", None) in calls


def test_js_defs():
    defs = _defs(extract_file("a.js", JS_FIXTURE))
    assert ("function", "build") in defs
    assert ("class", "App") in defs
    assert ("method", "handleClick") in defs
    assert ("function", "handler") in defs  # arrow function assigned to const


def test_js_imports():
    record = extract_file("a.js", JS_FIXTURE)
    by_module = {i["module"]: i for i in record["imports"]}
    assert by_module["react"]["default"] == "React"
    assert any(n["name"] == "useState" for n in by_module["react"]["names"])
    assert by_module["path"]["alias"] == "path"
    assert by_module["fs"]["kind"] == "require"


def test_js_exports_and_calls():
    record = extract_file("a.js", JS_FIXTURE)
    assert "build" in record["exports"]
    assert "App" in record["exports"]
    assert "extra" in record["exports"]  # module.exports.extra
    call_names = {c["name"] for c in record["calls"]}
    assert "build" in call_names
    assert "useState" in call_names


def test_python_main_guard():
    guarded = extract_file("run.py", b'def main():\n    pass\n\nif __name__ == "__main__":\n    main()\n')
    assert guarded["has_main_guard"] is True
    plain = extract_file("lib.py", b"def f():\n    pass\n")
    assert plain["has_main_guard"] is False


def test_js_default_export():
    record = extract_file("v.js", b"export default function render() {}\nexport function used() {}\n")
    assert record["default_export"] == "render"
    assert "render" in record["exports"]
    assert "used" in record["exports"]
    plain = extract_file("w.js", b"export function used() {}\n")
    assert plain["default_export"] is None


def test_python_dynamic_import():
    src = b'import importlib\nmod = importlib.import_module("plugins.fast")\n'
    record = extract_file("p.py", src)
    by_module = {i["module"]: i for i in record["imports"]}
    assert by_module["plugins.fast"]["kind"] == "dynamic"
    assert by_module["importlib"]["kind"] == "import"
    # non-literal specifiers stay invisible
    record2 = extract_file("q.py", b"import importlib\nmod = importlib.import_module(name)\n")
    assert all(i["kind"] != "dynamic" for i in record2["imports"])


def test_js_dynamic_import():
    record = extract_file("a.js", b'import("./chunk.js");\n')
    assert any(i["module"] == "./chunk.js" and i["kind"] == "dynamic"
               for i in record["imports"])


def test_cjs_export_keys():
    src = b'function parse() {}\nfunction stringify() {}\nmodule.exports = { parse, stringify };\n'
    assert set(extract_file("c.js", src)["exports"]) == {"parse", "stringify"}
    # `module.exports = <identifier>` has an unknowable shape: no names
    src2 = b'const api = {};\nmodule.exports = api;\n'
    assert extract_file("d.js", src2)["exports"] == []


def test_require_destructured_names():
    record = extract_file("i.js", b'const { parse, stringify: s } = require("./cjs.js");\nparse("x");\n')
    req = next(i for i in record["imports"] if i["kind"] == "require")
    assert req["module"] == "./cjs.js"
    assert {"name": "parse", "alias": None} in req["names"]
    assert {"name": "stringify", "alias": "s"} in req["names"]


def test_js_export_clause_aliases():
    # `export { x as default }` is a default export (documented in
    # _js_export_info); plain re-exports list their local names.
    src = (b"function render() {}\nfunction other() {}\n"
           b"export { render as default, other };\n")
    record = extract_file("v.js", src)
    assert record["default_export"] == "render"
    assert "render" in record["exports"]
    assert "other" in record["exports"]
    plain = extract_file("w.js", b"function a() {}\nfunction b() {}\n"
                                  b"export { a, b as c };\n")
    assert set(plain["exports"]) == {"a", "b"}
    assert plain["default_export"] is None


def test_js_call_args_record_callbacks():
    # Names in argument position are references: a callback passed to
    # register() must resolve later, or its def looks dead.
    src = (b"function handler() {}\nconst ns = {};\n"
           b"register(handler);\nregister(ns.handler);\n")
    record = extract_file("a.js", src)
    calls = [c for c in record["calls"] if c["name"] == "register"]
    assert [c["args"] for c in calls] == [["handler"], ["ns.handler"]]


def test_cjs_export_quoted_pair_keys():
    # module.exports with a quoted key exposes the unquoted name.
    src = (b"function parse() {}\nfunction stringify() {}\n"
           b"module.exports = { parse, \"stringify\": stringify };\n")
    assert set(extract_file("c.js", src)["exports"]) == {"parse", "stringify"}


def test_unsupported_file_type_raises():
    with pytest.raises(ValueError, match="unsupported file type"):
        extract_file("notes.txt", b"hi")
    with pytest.raises(ValueError, match="unsupported file type"):
        extract_file("Makefile", b"all:\n\techo hi\n")


def test_python_return_dotted_name():
    # `return helper.attr`: the returned name is a use of attr on helper,
    # so the receiver/name split runs on the dotted reference.
    record = extract_file("a.py", b"def build():\n    return helper.attr\n")
    assert any(c["name"] == "attr" and c["receiver"] == "helper"
               for c in record["calls"])


def test_python_call_arg_attribute():
    # An attribute in argument position is recorded dotted, not split:
    # `register(ns.handler)` keeps the receiver with the name.
    record = extract_file("a.py", b"register(ns.handler)\n")
    calls = [c for c in record["calls"] if c["name"] == "register"]
    assert [c["args"] for c in calls] == [["ns.handler"]]


def test_js_function_inside_class_method_is_method():
    # A function declared inside a method still sits under the class, so
    # it is recorded as a method of that class, not a top-level function.
    src = (b"class Widget {\n  render() {\n    function helper() {}\n"
           b"    helper();\n  }\n}\n")
    defs = _defs(extract_file("a.js", src))
    assert ("method", "helper") in defs
    assert defs[("method", "helper")]["parent"] == "Widget"
    assert ("function", "helper") not in defs


def test_js_dynamic_import_non_literal_specifier():
    # import(spec): a computed specifier is invisible, not an edge and
    # not a call; only literal dynamic imports are recorded.
    record = extract_file("a.js", b"import(spec);\n")
    assert record["imports"] == []
    assert record["calls"] == []


def test_js_require_non_literal_specifier():
    # require(spec): same ceiling as dynamic import, no literal no edge.
    record = extract_file("a.js", b"require(spec);\n")
    assert record["imports"] == []
    assert record["calls"] == []


def test_jsx_call_expression_not_double_counted():
    # `{foo()}` inside JSX: the call is recorded once, from the
    # call_expression node itself. The JSX-expression walk skips it so
    # it is not recorded a second time as a bare reference.
    src = (b"export default function Page() {\n"
           b"  return <div>{foo()}</div>;\n}\nfunction foo() {}\n")
    calls = extract_file("a.tsx", src)["calls"]
    assert [c["name"] for c in calls].count("foo") == 1


def test_jsx_member_expression_ref():
    # `{ns.handler}` inside JSX: the reference is the base object, so
    # the member expression contributes `ns`, not `handler`.
    src = (b"export default function Page() {\n"
           b"  return <div>{ns.handler}</div>;\n}\n")
    calls = extract_file("a.tsx", src)["calls"]
    assert any(c["name"] == "ns" and c["receiver"] is None for c in calls)


def test_bare_require_binds_no_names():
    # A require() that is not assigned to a variable binds no names:
    # the module edge exists, but there is nothing to resolve through it.
    record = extract_file("a.js", b'require("./m");\n')
    req = next(i for i in record["imports"] if i["kind"] == "require")
    assert req["module"] == "./m"
    assert req["names"] == []


def test_plain_assignment_exposes_nothing():
    # `x = 1` is not a member assignment, so it exposes no export names.
    assert extract_file("a.js", b"x = 1;\n")["exports"] == []


def test_unrelated_member_assignment_exposes_nothing():
    # `obj.prop = 1` is a member assignment but not a module.exports or
    # exports.* shape, so it exposes nothing.
    assert extract_file("a.js", b"obj.prop = 1;\n")["exports"] == []
