"""The report: one versioned JSON the dashboard and auto-PR both read.

Prompt 0.2 baked in now: the schema is versioned, per-ghost risk
reasons ride along with the scores, and the cost params used are
recorded so a dollar figure stays auditable. Day 4's API serves this;
the CLI prints it.
"""

from datetime import datetime, timezone

from ingest.ghosts import detect_ghosts

from . import cost, deadcode, debt, llm_pricing

REPORT_SCHEMA = 1


def build_report(records, graph, sources, repo_label="local"):
    """Assemble the full analysis report from pipeline outputs."""
    ghosts = detect_ghosts(records, graph)
    scored = deadcode.score_ghosts(ghosts, records, sources)
    cost_summary = cost.summarize(scored, records, graph, sources)
    debt_report = debt.analyze_debt(records, graph, sources)
    enriched = cost_summary["ghosts"]
    return {
        "schema": REPORT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": repo_label,
        "summary": {
            "files": len(records),
            "total_loc": sum(r["loc"] for r in records),
            "ghost_files": sum(1 for g in enriched
                               if g["ghost_kind"] == "file"),
            "ghost_symbols": sum(1 for g in enriched
                                 if g["ghost_kind"] == "symbol"),
            "ghost_loc": cost_summary["ghost_loc"],
            "annual_burn_usd": cost_summary["annual_burn_usd"],
            "debt": {
                "circular_imports": len(debt_report["circular_imports"]["cycles"]),
                "duplicate_groups": len(debt_report["duplicates"]),
                "huge_files": len(debt_report["huge_files"]),
            },
        },
        "ghosts": enriched,
        "debt": debt_report,
        "cost_model": {
            "params": cost_summary["params"],
            "llm_pricing": llm_pricing.estimate_llm_cost(
                cost_summary["ghost_loc"]),
        },
    }
