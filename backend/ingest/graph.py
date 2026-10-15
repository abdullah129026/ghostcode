"""Dependency graph built from symbol records.

Day 1 edges: file -> symbol (defines), file -> module specifier (imports).
Call/reference edges and ghost detection land on Day 2 on top of this graph,
so this module stays the single place a graph gets built.
"""

import networkx as nx

from . import schema


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
    return graph


def graph_json(graph):
    """Serialize the graph to the versioned graph JSON contract."""
    nodes = [{"id": node, **attrs} for node, attrs in graph.nodes(data=True)]
    edges = [{"from": src, "to": dst, **attrs}
             for src, dst, attrs in graph.edges(data=True)]
    return {"schema": schema.SCHEMA_VERSION, "nodes": nodes, "edges": edges}
