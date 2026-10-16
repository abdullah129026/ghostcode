"""Dependency graph built from symbol records.

Day 1 edges: file -> symbol (defines), file -> module specifier (imports).
Day 2 adds resolved edges on top: file -> file (imports_resolved),
file -> symbol (calls, uses). This module stays the single place a graph
gets built; resolution logic itself lives in resolve.py.
"""

import networkx as nx

from . import resolve, schema


def file_id(relpath):
    return f"file:{relpath}"


def symbol_id(relpath, kind, name, seen):
    base = f"sym:{relpath}::{kind}:{name}"
    n = seen.get(base, 0)
    seen[base] = n + 1
    return base if n == 0 else f"{base}#{n}"


def module_id(specifier):
    return f"module:{specifier}"


def build_graph(file_records):
    """Return a networkx DiGraph with file, symbol, and module nodes."""
    graph = nx.DiGraph()
    seen = {}
    symbol_index = {}
    for record in file_records:
        fid = file_id(record["path"])
        graph.add_node(fid, kind="file", path=record["path"],
                       loc=record["loc"], language=record["language"])
        for imp in record["imports"]:
            mid = module_id(imp["module"])
            if not graph.has_node(mid):
                graph.add_node(mid, kind="module", specifier=imp["module"])
            graph.add_edge(fid, mid, type="imports")
        for definition in record["defs"]:
            sid = symbol_id(record["path"], definition["kind"],
                            definition["name"], seen)
            graph.add_node(sid, kind="symbol", sym_kind=definition["kind"],
                           name=definition["name"], file=record["path"],
                           lineno=definition["lineno"],
                           end_lineno=definition["end_lineno"],
                           parent=definition["parent"])
            graph.add_edge(fid, sid, type="defines")
            key = (record["path"], definition["kind"], definition["name"])
            symbol_index.setdefault(key, []).append(sid)
    # The single lookup table for (path, kind, name) -> node ids, so
    # resolution never re-derives the id scheme and cannot drift from it.
    graph.graph["symbol_index"] = symbol_index
    return graph


def add_resolved_edges(graph, records, root):
    """Append resolved import/call/use edges to a graph from build_graph.

    Keeps graph construction in one place: resolution lives in resolve.py,
    but only this module mutates the graph.
    """
    index = graph.graph.get("symbol_index", {})
    seen = set()
    for src, dst, kind in resolve.import_edges(root, records):
        if graph.has_node(file_id(src)) and graph.has_node(file_id(dst)):
            key = (src, dst, kind)
            if key not in seen:
                seen.add(key)
                graph.add_edge(file_id(src), file_id(dst), type="imports_resolved")
    for src, dpath, dkind, dname, kind in (resolve.call_edges(root, records)
                                           + resolve.use_edges(root, records)):
        for sid in index.get((dpath, dkind, dname), []):
            key = (src, sid, kind)
            if key not in seen:
                seen.add(key)
                graph.add_edge(file_id(src), sid, type=kind)


def graph_json(graph):
    """Serialize the graph to the versioned graph JSON contract."""
    nodes = [{"id": node, **attrs} for node, attrs in graph.nodes(data=True)]
    edges = [{"from": src, "to": dst, **attrs}
             for src, dst, attrs in graph.edges(data=True)]
    return {"schema": schema.SCHEMA_VERSION, "nodes": nodes, "edges": edges}
