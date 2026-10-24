"""Job worker tests: the pipeline runs on a fixture checkout, clones are
always cleaned up, and failures settle as job errors instead of raising."""

import os
import shutil
import subprocess
from unittest import mock

import pytest

from api import jobs
from api.jobs import JobFailed, JobStore, run_job
from ingest.walk import WalkError

FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "ingest", "fixtures", "py_app"
)


def _fake_clone_from_fixture(monkeypatch, record):
    def fake_clone(repo_url, dest):
        record["dest"] = dest
        for name in os.listdir(FIXTURE):
            src = os.path.join(FIXTURE, name)
            dst = os.path.join(dest, name)
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)

    monkeypatch.setattr(jobs, "_clone", fake_clone)


def test_successful_job_serves_fixture_report(monkeypatch):
    record = {}
    _fake_clone_from_fixture(monkeypatch, record)
    store = JobStore()
    job = store.create("https://github.com/acme/widgets.git")
    run_job(store, job.id)
    assert job.status == "done"
    assert job.report["schema"] == 2
    assert job.report["repo"] == "acme/widgets"
    assert job.report["summary"]["files"] > 0
    assert job.finished_at is not None
    # the clone never survives the job
    assert not os.path.exists(record["dest"])


def test_clone_failure_settles_as_job_error(monkeypatch):
    def boom(repo_url, dest):
        raise JobFailed("clone_failed", "nope")

    monkeypatch.setattr(jobs, "_clone", boom)
    store = JobStore()
    job = store.create("https://github.com/acme/widgets.git")
    run_job(store, job.id)
    assert job.status == "error"
    assert job.error == {"code": "clone_failed", "message": "nope"}
    assert job.finished_at is not None


def test_unknown_job_id_is_noop():
    run_job(JobStore(), "0" * 32)  # must not raise


def test_store_evicts_oldest_first():
    store = JobStore(max_jobs=2)
    first = store.create("https://github.com/a/1.git")
    store.create("https://github.com/a/2.git")
    store.create("https://github.com/a/3.git")
    assert store.get(first.id) is None


def test_store_never_evicts_running_job():
    store = JobStore(max_jobs=2)
    running = store.create("https://github.com/a/1.git")
    running.status = "running"
    settled = store.create("https://github.com/a/2.git")
    store.create("https://github.com/a/3.git")
    assert store.get(running.id) is not None
    assert store.get(settled.id) is None


def test_clone_timeout_maps_to_clone_timeout(monkeypatch):
    monkeypatch.setattr(
        "subprocess.run",
        mock.Mock(side_effect=subprocess.TimeoutExpired("git clone", 120)),
    )
    with pytest.raises(JobFailed) as exc_info:
        jobs._clone("https://github.com/acme/widgets.git", "/tmp/nope")
    assert exc_info.value.code == "clone_timeout"
    assert "120" in exc_info.value.message


def test_clone_failure_truncates_stderr_to_300_chars(monkeypatch):
    proc = mock.Mock(returncode=128, stdout="", stderr="fatal: boom\n" * 100)
    monkeypatch.setattr("subprocess.run", mock.Mock(return_value=proc))
    with pytest.raises(JobFailed) as exc_info:
        jobs._clone("https://github.com/acme/widgets.git", "/tmp/nope")
    assert exc_info.value.code == "clone_failed"
    assert len(exc_info.value.message) <= 300
    assert exc_info.value.message.startswith("fatal: boom")


def test_pipeline_walk_error_maps_to_repo_too_large(monkeypatch):
    monkeypatch.setattr(
        jobs, "analyze", mock.Mock(side_effect=WalkError("cap exceeded"))
    )
    with pytest.raises(JobFailed) as exc_info:
        jobs._run_pipeline("/tmp/nope", "acme/widgets")
    assert exc_info.value.code == "repo_too_large"
