"""Shared record shapes for the ingestion pipeline.

The schema version is bumped whenever a field is added, renamed, or
removed, so old reports and the dashboard can keep reading what they know.
"""

SCHEMA_VERSION = 3


def file_record(path, language, loc, imports, defs, exports, calls,
               has_main_guard=False, default_export=None):
    return {
        "path": path,
        "language": language,
        "loc": loc,
        "imports": imports,
        "defs": defs,
        "exports": exports,
        "calls": calls,
        # True when a Python file has an `if __name__ == "__main__":` block:
        # it is run, not imported, so it is an entry point, not a ghost.
        "has_main_guard": has_main_guard,
        # Name of the default-exported symbol for JS/TS modules (else None).
        "default_export": default_export,
    }


def import_record(module, names=(), alias=None, lineno=None, kind="import"):
    return {
        "module": module,
        "names": list(names),
        "alias": alias,
        "lineno": lineno,
        "kind": kind,  # "import" | "from" | "require"
    }


def def_record(kind, name, lineno, end_lineno, parent=None,
               decorated=False):
    return {
        "kind": kind,  # "function" | "class" | "method"
        "name": name,
        "lineno": lineno,
        "end_lineno": end_lineno,
        "parent": parent,
        # True when the def carries a decorator (@app.get, @dataclass):
        # the runtime invokes or transforms it, so no static call edge
        # ever points at it. Added in schema 2 (Day 7 dogfood).
        "decorated": decorated,
    }


def call_record(name, receiver, lineno, args=()):
    return {
        "name": name,
        "receiver": receiver,
        "lineno": lineno,
        # Names referenced in argument position (`Depends(_limit)`,
        # `Thread(target=_run)`): a reference is a use. Added in schema 3
        # (Day 7 dogfood); nested calls are recorded separately.
        "args": list(args),
    }
