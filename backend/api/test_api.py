"""API tests: health, the error envelope, and the analyze flow."""

import re
import time

from fastapi.testclient import TestClient

from api import jobs
from api.app import create_app
from api.security import RateLimiter

JOB_ID_RE = re.compile(r"^[0-9a-f]{32}$")
CANNED_REPORT = {"schema": 1, "repo": "acme/widgets", "summary": {"files": 3}}


def _client():
    return TestClient(create_app())


def _wait_for(client, job_id, want="done", timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        body = client.get(f"/jobs/{job_id}").json()
        if body["status"] == want:
            return body
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} never reached {want}")


def _fake_run_done(monkeypatch):
    def fake_run(store, job_id):
        job = store.get(job_id)
        job.status = "done"
        job.report = CANNED_REPORT

    monkeypatch.setattr(jobs, "run_job", fake_run)


def test_health():
    resp = _client().get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["service"] == "ghostcode-api"


def test_unknown_route_uses_error_envelope():
    resp = _client().get("/nope")
    assert resp.status_code == 404
    assert resp.json() == {"error": {"code": "not_found", "message": "Not Found"}}


def test_wrong_method_uses_error_envelope():
    resp = _client().post("/health")
    assert resp.status_code == 405
    assert resp.json()["error"]["code"] == "method_not_allowed"


def test_analyze_rejects_off_host_url():
    resp = _client().post("/analyze", json={"repo_url": "https://gitlab.com/a/b"})
    assert resp.status_code == 422
    assert resp.json() == {
        "error": {
            "code": "invalid_repo_url",
            "message": "v1 only analyzes public repos on github.com",
        }
    }


def test_analyze_rejects_credentials_in_url():
    resp = _client().post(
        "/analyze", json={"repo_url": "https://user:tok@github.com/a/b"}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "credentials_in_url"


def test_analyze_rejects_missing_body():
    resp = _client().post("/analyze", json={})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_request"


def test_analyze_flow_serves_report(monkeypatch):
    _fake_run_done(monkeypatch)
    client = _client()
    resp = client.post(
        "/analyze", json={"repo_url": "https://github.com/acme/widgets"}
    )
    assert resp.status_code == 202
    accepted = resp.json()
    assert JOB_ID_RE.match(accepted["job_id"])
    assert accepted["status"] == "queued"
    assert accepted["poll_url"] == f"/jobs/{accepted['job_id']}"

    status = _wait_for(client, accepted["job_id"])
    assert status["repo"] == "acme/widgets"
    assert status["report_url"] == f"/report/{accepted['job_id']}"

    report = client.get(f"/report/{accepted['job_id']}")
    assert report.status_code == 200
    assert report.json() == CANNED_REPORT


def test_report_while_running_is_409(monkeypatch):
    monkeypatch.setattr(jobs, "run_job", lambda store, job_id: None)
    client = _client()
    job_id = client.post(
        "/analyze", json={"repo_url": "https://github.com/acme/widgets"}
    ).json()["job_id"]
    resp = client.get(f"/report/{job_id}")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "not_ready"


def test_report_on_failed_job_carries_job_error(monkeypatch):
    def fake_run(store, job_id):
        job = store.get(job_id)
        job.status = "error"
        job.error = {"code": "clone_failed", "message": "nope"}

    monkeypatch.setattr(jobs, "run_job", fake_run)
    client = _client()
    job_id = client.post(
        "/analyze", json={"repo_url": "https://github.com/acme/widgets"}
    ).json()["job_id"]
    status = _wait_for(client, job_id, want="error")
    assert status["error"] == {"code": "clone_failed", "message": "nope"}
    resp = client.get(f"/report/{job_id}")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "clone_failed"


def test_unknown_job_id_is_404_envelope():
    client = _client()
    for bad in ("0" * 32, "not-a-job-id"):
        resp = client.get(f"/jobs/{bad}")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "not_found"


def test_analyze_rate_limit_returns_429(monkeypatch):
    monkeypatch.setattr(jobs, "run_job", lambda store, job_id: None)
    client = _client()
    client.app.state.analyze_limiter = RateLimiter(per_minute=60, burst=1)
    payload = {"repo_url": "https://github.com/acme/widgets"}
    assert client.post("/analyze", json=payload).status_code == 202
    resp = client.post("/analyze", json=payload)
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert resp.json()["error"]["code"] == "rate_limited"
