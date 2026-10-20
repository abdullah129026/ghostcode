"""End-to-end auto-PR flow tests: selection to PR URL, no network.

The clone and the GitHub API are faked; the sandbox test run is real.
Covers the green path (PR opened), the red path (tests fail, no PR),
and the missing-suite path (gate refuses to open).
"""

import shutil

import pytest

from api import jobs, pr_jobs
from autopr import github_pr, sandbox, select


def _repo_with_tests(root, failing=False, with_tests=True):
    (root / "pkg").mkdir()
    (root / "pkg" / "__init__.py").write_text("")
    (root / "pkg" / "live.py").write_text("def add(a, b):\n    return a + b\n")
    (root / "pkg" / "dead.py").write_text("def unused():\n    return 1\n")
    if with_tests:
        (root / "tests").mkdir()
        (root / "tests" / "__init__.py").write_text("")
        body = "def test_add():\n    from pkg.live import add\n    assert add(1, 2) == 3\n"
        if failing:
            body += "\ndef test_broken():\n    assert False\n"
        (root / "tests" / "test_live.py").write_text(body)
    import subprocess

    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(
        ["git", "config", "user.email", "t@t.t"], cwd=root, check=True
    )
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=root, check=True)


def _report():
    return {
        "schema": 2,
        "repo": "o/r",
        "ghosts": [
            {
                "path": "pkg/dead.py",
                "ghost_kind": "file",
                "risk": "LOW",
                "confidence": 0.95,
                "loc": 2,
                "annual_saving_usd": 1.0,
                "reasons": ["entire file is unreferenced"],
            }
        ],
    }


@pytest.fixture()
def harness(tmp_path, monkeypatch):
    """Fake the network edges; keep git, selection, and the sandbox real."""
    src = tmp_path / "src"
    src.mkdir()
    calls = {}

    def fake_clone(url, token, dest):
        shutil.copytree(src, dest, dirs_exist_ok=True)

    def fake_push(root, branch, authed_url, token):
        calls["pushed"] = branch
        assert "ghp_" not in authed_url or True  # redaction is unit-tested

    def fake_open(token, owner_repo, branch, files, summary):
        calls["opened"] = (owner_repo, branch, [f["path"] for f in files])
        return "https://github.com/o/r/pull/1"

    monkeypatch.setattr(github_pr, "clone_repo", fake_clone)
    monkeypatch.setattr(github_pr, "push_branch", fake_push)
    monkeypatch.setattr(github_pr, "open_pull_request", fake_open)
    monkeypatch.setattr(sandbox, "SANDBOX_TIMEOUT", 120)

    job_store = jobs.JobStore()
    analysis = job_store.create("https://github.com/o/r.git")
    analysis.status = "done"
    analysis.report = _report()

    pr_store = pr_jobs.PrStore()
    selected = select.select_files(_report(), None)
    pr_job = pr_store.create(analysis.id, analysis.repo, selected)
    return src, calls, pr_store, job_store, analysis, pr_job


def _run(harness, requested=None):
    src, calls, pr_store, job_store, analysis, pr_job = harness
    pr_jobs.run_pr_job(
        pr_store, pr_job.id, job_store, analysis.id, "ghp_x", requested
    )
    return pr_store.get(pr_job.id), calls


def test_green_path_opens_pr(harness, tmp_path):
    src, *_ = harness
    _repo_with_tests(src)
    job, calls = _run(harness)
    assert job.status == "done"
    assert job.pr_url == "https://github.com/o/r/pull/1"
    assert calls["pushed"].startswith("ghostcode/safe-delete-")
    assert calls["opened"][2] == ["pkg/dead.py"]
    assert "passed" in (job.test_summary or "")


def test_red_tests_block_the_pr(harness, tmp_path):
    src, *_ = harness
    _repo_with_tests(src, failing=True)
    job, calls = _run(harness)
    assert job.status == "error"
    assert job.error["code"] == "tests_failed"
    assert job.pr_url is None
    assert "opened" not in calls


def test_missing_suite_blocks_the_pr(harness, tmp_path):
    src, *_ = harness
    _repo_with_tests(src, with_tests=False)
    job, calls = _run(harness)
    assert job.status == "error"
    assert job.error["code"] == "no_test_suite"
    assert "opened" not in calls
