"""Extractor fixtures: hand-written snippets with known symbols.

These pin the parser contract. A false negative here means the graph is
built on lies, so keep the fixtures small and the assertions exact.
"""

from ingest.extract import extract_file


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
