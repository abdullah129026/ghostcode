"""Heuristic cost model: dead code priced as an annual burn.

annual_saving = ghost_loc x COST_PER_LOC x (1 + COMPLEXITY_WEIGHT x mean_cc)

COST_PER_LOC ($0.50) is the prompt's number. The parameters live in
COST_PARAMS so an org can tune them later (prompt 0.2, design hook);
the report records the params it ran with so numbers stay auditable.

Complexity is cyclomatic-ish, counted from branch keywords in the
function body text. It is a heuristic, not a proof: it only scales the
dollar figure, it never changes what gets flagged.
"""

import re

# Tune per org. Recorded in every report so a dollar figure is auditable.
COST_PARAMS = {
    "cost_per_loc": 0.50,
    "complexity_weight": 0.15,
    "chars_per_line": 40,  # used only by the LLM pricing estimate
}

_PY_BRANCH = re.compile(rb"\b(if|elif|for|while|except|with|and|or|assert)\b")
_JS_BRANCH = re.compile(
    rb"\b(if|for|while|case|catch)\b|&&|\|\||\?\?|(?<![?.])\?(?![?.])"
)


def complexity(body, language):
    """Branch count + 1 for a function body (bytes)."""
    pattern = _JS_BRANCH if language in ("javascript", "typescript", "tsx") else _PY_BRANCH
    return 1 + len(pattern.findall(body))


def _body_lines(source, lineno, end_lineno):
    return b"\n".join(source.split(b"\n")[lineno - 1 : end_lineno])


def file_mean_complexity(record, sources):
    """Mean function/method complexity for a file, 0.0 when unknown."""
    source = sources.get(record["path"])
    if source is None:
        return 0.0
    scores = [
        complexity(_body_lines(source, d["lineno"], d["end_lineno"]),
                   record["language"])
        for d in record["defs"]
        if d["kind"] in ("function", "method")
    ]
    return sum(scores) / len(scores) if scores else 0.0


def symbol_complexity(node_attrs, record, sources):
    """Complexity of one symbol's own body, 0.0 when unknown."""
    source = sources.get(node_attrs.get("file", ""))
    if source is None:
        return 0.0
    return complexity(
        _body_lines(source, node_attrs["lineno"], node_attrs["end_lineno"]),
        record["language"],
    )


def annual_saving(loc, mean_cc, params=COST_PARAMS):
    """Dollars per year a deletion of `loc` lines at `mean_cc` saves."""
    return round(
        loc * params["cost_per_loc"] * (1 + params["complexity_weight"] * mean_cc),
        2,
    )


def summarize(scored_ghosts, records, graph, sources, params=COST_PARAMS):
    """Attach loc and annual saving to each scored ghost, plus totals."""
    by_path = {r["path"]: r for r in records}
    enriched = []
    for ghost in scored_ghosts:
        record = by_path.get(ghost["path"], {})
        if ghost["ghost_kind"] == "file":
            loc = record.get("loc", 0)
            mean_cc = file_mean_complexity(record, sources) if record else 0.0
        else:
            node = graph.nodes.get(ghost["id"], {})
            loc = max(0, node.get("end_lineno", 0) - node.get("lineno", 0) + 1)
            mean_cc = symbol_complexity(node, record, sources) if record else 0.0
        enriched.append(
            {**ghost, "loc": loc,
             "annual_saving_usd": annual_saving(loc, mean_cc, params)}
        )
    enriched.sort(key=lambda g: -g["annual_saving_usd"])
    return {
        "annual_burn_usd": round(sum(g["annual_saving_usd"] for g in enriched), 2),
        "ghost_loc": sum(g["loc"] for g in enriched),
        "params": dict(params),
        "ghosts": enriched,
    }
