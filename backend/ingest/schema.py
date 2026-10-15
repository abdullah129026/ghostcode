"""Shared record shapes for the ingestion pipeline.

The schema version is bumped whenever a field is added, renamed, or
removed, so old reports and the dashboard can keep reading what they know.
"""

SCHEMA_VERSION = 1


def file_record(path, language, loc, imports, defs, exports, calls):
    return {
        "path": path,
        "language": language,
        "loc": loc,
        "imports": imports,
        "defs": defs,
        "exports": exports,
        "calls": calls,
    }


def import_record(module, names=(), alias=None, lineno=None, kind="import"):
    return {
        "module": module,
        "names": list(names),
        "alias": alias,
        "lineno": lineno,
        "kind": kind,  # "import" | "from" | "require"
    }


def def_record(kind, name, lineno, end_lineno, parent=None):
    return {
        "kind": kind,  # "function" | "class" | "method"
        "name": name,
        "lineno": lineno,
        "end_lineno": end_lineno,
        "parent": parent,
    }


def call_record(name, receiver, lineno):
    return {"name": name, "receiver": receiver, "lineno": lineno}
