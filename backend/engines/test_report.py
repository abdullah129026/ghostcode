"""Report tests: the assembled JSON contract the dashboard will read."""

import json
from datetime import datetime

from engines import read_sources
from engines.report import REPORT_SCHEMA, build_report
from ingest.cli import analyze, main
from ingest.graph import add_resolved_edges, build_graph


def _write(tmp_path, rel, text):
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _report(tmp_path):
    _write(tmp_path, "main.py",
           'from live import run\n\nif __name__ == "__main__":\n    run()\n')
    _write(tmp_path, "live.py", "def run():\n    print('live')\n")
    _write(tmp_path, "dead.py", "def gone():\n    return 1\n")
    root = str(tmp_path)
    records = analyze(root)
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    return build_report(records, graph, read_sources(root, records),
                        repo_label=root)


def test_report_contract(tmp_path):
    report = _report(tmp_path)
    assert report["schema"] == REPORT_SCHEMA
    datetime.fromisoformat(report["generated_at"])  # parses
    summary = report["summary"]
    assert summary["files"] == 3
    assert summary["ghost_files"] == 1
    assert summary["ghost_symbols"] == 1
    assert summary["ghost_loc"] == sum(g["loc"] for g in report["ghosts"])
    assert summary["annual_burn_usd"] == sum(
        g["annual_saving_usd"] for g in report["ghosts"])
    assert set(summary["debt"]) == {"circular_imports", "duplicate_groups",
                                    "huge_files"}
    for ghost in report["ghosts"]:
        assert {"confidence", "risk", "reasons", "loc",
                "annual_saving_usd"} <= set(ghost)
        assert ghost["risk"] in ("LOW", "MED", "HIGH")
        assert ghost["reasons"], "a risk flag with no reason is unactionable"
    assert report["cost_model"]["params"]["cost_per_loc"] == 0.50
    assert report["cost_model"]["llm_pricing"]["model"]
    json.dumps(report)  # the dashboard consumes this as JSON


def test_cli_report_flag(tmp_path, capsys):
    _write(tmp_path, "main.py", 'if __name__ == "__main__":\n    print("hi")\n')
    assert main(["--report", str(tmp_path)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["schema"] == REPORT_SCHEMA
    assert payload["summary"]["files"] == 1
