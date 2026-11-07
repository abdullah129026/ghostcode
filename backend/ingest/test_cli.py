"""CLI entry point: main() output modes and error exit codes.

main() was the only untested path in ingest/cli.py — analyze() is covered
through test_graph.py, but no test ever ran the argument parsing, the
--symbols/--ghosts/--report branches, or the WalkError/OSError exits.
"""

import json
import os

from ingest import cli, schema

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
PY_APP = os.path.join(FIXTURES, "py_app")


def _run(capsys, argv):
    assert cli.main(argv) == 0
    return json.loads(capsys.readouterr().out)


def test_main_prints_graph_json_by_default(capsys):
    payload = _run(capsys, [PY_APP])
    assert payload["schema"] == schema.SCHEMA_VERSION
    assert payload["nodes"]
    assert isinstance(payload["edges"], list)


def test_main_symbols_flag_prints_raw_records(capsys):
    payload = _run(capsys, [PY_APP, "--symbols"])
    assert payload["schema"] == schema.SCHEMA_VERSION
    assert payload["files"]
    assert all("path" in f for f in payload["files"])


def test_main_ghosts_flag_prints_ghost_report(capsys):
    payload = _run(capsys, [PY_APP, "--ghosts"])
    assert payload["schema"] == schema.SCHEMA_VERSION
    assert [f["path"] for f in payload["files"]] == ["truly_dead.py"]


def test_main_report_flag_prints_full_report(capsys):
    payload = _run(capsys, [PY_APP, "--report"])
    assert payload["schema"] == 2
    assert payload["summary"]["files"] > 0
    assert payload["summary"]["ghost_files"] == 1
    assert "graph" in payload and "cost_model" in payload


def test_main_returns_2_for_missing_repo(capsys):
    assert cli.main(["/definitely/not/a/repo"]) == 2
    assert "ghostcode: not a directory" in capsys.readouterr().err


def test_main_returns_2_when_repo_unreadable(monkeypatch, capsys):
    def boom(root):
        raise OSError("permission denied")

    monkeypatch.setattr(cli, "analyze", boom)
    assert cli.main([PY_APP]) == 2
    assert "ghostcode: cannot read repo" in capsys.readouterr().err
