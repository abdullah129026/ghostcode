"""GhostCode ingest CLI: parse a repo checkout, print its dependency graph.

Usage:
    python -m ingest.cli /path/to/repo [--symbols]

Prints the versioned graph JSON to stdout (the contract the dashboard and
auto-PR consume). --symbols prints the raw per-file symbol records instead.
"""

import argparse
import json
import sys

from .extract import extract_file
from .ghosts import detect_ghosts
from .graph import add_resolved_edges, build_graph, graph_json
from .walk import walk_repo, WalkError
from . import schema


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Parse a repo and print its dependency graph as JSON.")
    parser.add_argument("repo", help="path to a local repo checkout")
    parser.add_argument("--symbols", action="store_true",
                        help="print raw symbol records instead of graph JSON")
    parser.add_argument("--ghosts", action="store_true",
                        help="print the ghost report (dead files and symbols)")
    return parser.parse_args(argv)


def analyze(root):
    records = []
    for relpath, abspath, _language in walk_repo(root):
        with open(abspath, "rb") as handle:
            records.append(extract_file(relpath, handle.read()))
    return records


def main(argv=None):
    args = parse_args(argv)
    try:
        records = analyze(args.repo)
    except WalkError as exc:
        print(f"ghostcode: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ghostcode: cannot read repo: {exc}", file=sys.stderr)
        return 2
    if args.ghosts:
        graph = build_graph(records)
        add_resolved_edges(graph, records, args.repo)
        payload = detect_ghosts(records, graph)
    elif args.symbols:
        payload = {"schema": schema.SCHEMA_VERSION, "files": records}
    else:
        payload = graph_json(build_graph(records))
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())
