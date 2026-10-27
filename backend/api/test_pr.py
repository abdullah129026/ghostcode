"""API tests: POST /pr validation and the /pr-jobs poll flow."""

import time

from fastapi.testclient import TestClient

from api import pr_jobs
from api.app import create_app
from autopr.github_pr import GitError

TOKEN = "ghp_testtoken_abc123"

CANNED_REPORT = {
    "schema": 2,
    "repo": "acme/widgets",
    "ghosts": [
        {
            "path": "dead.py",
            "ghost_kind": "file",
            "risk": "LOW",
            "confidence": 0.95,
            "loc": 10,
            "annual_saving_usd": 4.2,
            "reasons": ["entire file is unreferenced"],
        },
        {
            "path": "risky.py",
            "ghost_kind": "file",
            "risk": "MED",
            "confidence": 0.7,
            "loc": 20,
            "annual_saving_usd": 8.0,
            "reasons": ["repo uses getattr"],
        },
    ],
}


def _client():
    return TestClient(create_app())


def _done_job(client):
    store = client.app.state.jobs
    job = store.create("https://github.com/acme/widgets.git")
    job.status = "done"
    job.report = CANNED_REPORT
    return job


def test_pr_rejects_unknown_and_unready_jobs():
    client = _client()
    body = {"job_id": "0" * 32, "github_token": TOKEN}
    assert client.post("/pr", json=body).status_code == 404
    assert client.post("/pr", json={**body, "job_id": "nope"}).status_code == 422

    store = client.app.state.jobs
    queued = store.create("https://github.com/acme/widgets.git")
    resp = client.post(
        "/pr", json={**body, "job_id": queued.id}
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "not_ready"


def test_pr_rejects_bad_selection_before_spawning():
    client = _client()
    job = _done_job(client)
    resp = client.post(
        "/pr",
        json={
            "job_id": job.id,
            "github_token": TOKEN,
            "files": ["risky.py", "../evil.py"],
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_file_selection"
    assert len(client.app.state.pr_jobs._jobs) == 0


def _wait_pr(client, pr_id, want="error", timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/pr-jobs/{pr_id}").json()
        if body["status"] == want:
            return body
        time.sleep(0.05)
    raise AssertionError(f"pr job {pr_id} never reached {want}")


def test_pr_accepts_and_worker_fails_closed(monkeypatch):
    # the worker's clone fails deterministically; the API must settle
    # the job as errored without leaking the token anywhere.
    def no_clone(url, dest, token=""):
        raise GitError("clone_failed", "nope")

    monkeypatch.setattr(pr_jobs.github_pr, "clone_repo", no_clone)
    client = _client()
    job = _done_job(client)
    resp = client.post(
        "/pr",
        json={"job_id": job.id, "github_token": TOKEN, "files": ["dead.py"]},
    )
    assert resp.status_code == 202
    pr_id = resp.json()["pr_job_id"]
    assert resp.json()["poll_url"] == f"/pr-jobs/{pr_id}"

    body = _wait_pr(client, pr_id)
    assert body["status"] == "error"
    assert body["error"]["code"] == "clone_failed"
    assert body["files"] == ["dead.py"]
    assert body["pr_url"] is None
    assert TOKEN not in resp.text
    status_text = client.get(f"/pr-jobs/{pr_id}").text
    assert TOKEN not in status_text


def test_pr_job_unknown_id_404():
    assert _client().get("/pr-jobs/" + "0" * 32).status_code == 404


def test_pr_store_never_evicts_running_job():
    store = pr_jobs.PrStore(max_jobs=2)
    running = store.create("job-a", "acme/widgets", [])
    settled = store.create("job-b", "acme/widgets", [])
    running.status = "running"
    store.create("job-c", "acme/widgets", [])
    assert store.get(running.id) is running
    assert store.get(settled.id) is None
    assert len(store._jobs) == 2


def test_pr_store_grows_when_every_job_running():
    store = pr_jobs.PrStore(max_jobs=1)
    first = store.create("job-a", "acme/widgets", [])
    first.status = "running"
    store.create("job-b", "acme/widgets", [])
    assert store.get(first.id) is first
    assert len(store._jobs) == 2
