"""Analysis jobs: clone a repo, run the pipeline, always clean up.

POST /analyze returns 202 immediately and the work happens on a daemon
thread (0.2 baked in now: analysis outgrows request timeouts). Job state
is in-memory, so a restart drops running jobs; finished jobs are capped
and the oldest are evicted. The clone lives in a tempdir that is removed
when the job settles, success or failure.
"""

import logging
import os
import subprocess
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from engines import read_sources
from engines.report import build_report
from ingest.cli import analyze
from ingest.graph import add_resolved_edges, build_graph
from ingest.walk import WalkError

from .security import env_int, repo_label

log = logging.getLogger("ghostcode.jobs")

CLONE_TIMEOUT = env_int("GHOSTCODE_CLONE_TIMEOUT", 120)
MAX_JOBS = env_int("GHOSTCODE_MAX_JOBS", 100)


class JobFailed(Exception):
    """A job-settling failure with an API-facing code and message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Job:
    id: str
    repo_url: str  # canonical https URL, credential-free by construction
    repo: str  # "owner/repo" label, safe for logs and the UI
    status: str = "queued"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: datetime | None = None
    finished_at: datetime | None = None
    report: dict | None = None
    error: dict | None = None


class JobStore:
    """Thread-safe in-memory job registry with oldest-first eviction."""

    def __init__(self, max_jobs: int = MAX_JOBS):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max_jobs = max_jobs

    def create(self, repo_url: str) -> Job:
        job = Job(
            id=uuid.uuid4().hex, repo_url=repo_url, repo=repo_label(repo_url)
        )
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > self._max_jobs:
                # never evict a running job: its poll URL is live and its
                # report is being computed. If every job is running, the
                # store grows until one settles (bounded by the clone
                # timeout and the walk caps, so this is temporary).
                candidates = [
                    j
                    for j in self._jobs.values()
                    if j.status != "running" and j.id != job.id
                ]
                if not candidates:
                    break
                oldest = min(candidates, key=lambda j: j.created_at)
                del self._jobs[oldest.id]
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)


def _clone(repo_url: str, dest: str) -> None:
    """Shallow single-branch clone. Raises JobFailed on any failure."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    try:
        proc = subprocess.run(
            [
                "git", "clone", "--depth", "1", "--single-branch",
                "--no-tags", "--", repo_url, dest,
            ],
            capture_output=True,
            text=True,
            timeout=CLONE_TIMEOUT,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise JobFailed(
            "clone_timeout", f"clone took longer than {CLONE_TIMEOUT}s"
        )
    if proc.returncode != 0:
        # stderr can echo the URL; ours never carries credentials, and the
        # message is still truncated before it reaches the client.
        detail = "; ".join((proc.stderr or "git clone failed").splitlines())
        raise JobFailed("clone_failed", detail[:300] or "git clone failed")


def _run_pipeline(root: str, label: str) -> dict:
    try:
        records = analyze(root)
    except WalkError as exc:
        raise JobFailed("repo_too_large", str(exc))
    except OSError as exc:
        raise JobFailed(
            "unreadable_checkout", f"could not read cloned repo: {exc}"
        )
    graph = build_graph(records)
    add_resolved_edges(graph, records, root)
    return build_report(
        records, graph, read_sources(root, records), repo_label=label
    )


def run_job(store: JobStore, job_id: str) -> None:
    """Worker entrypoint: settle one job. Never raises, never leaks a clone."""
    job = store.get(job_id)
    if job is None:
        return
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    log.info("job started job_id=%s repo=%s", job.id, job.repo)
    try:
        # ponytail: the clone download itself is uncapped (a partial clone
        # would starve the analysis of file contents); the walk's file caps
        # bound the analysis and the clone timeout bounds the download.
        # Revisit if giant repos show up in practice.
        with tempfile.TemporaryDirectory(prefix="ghostcode-") as tmp:
            _clone(job.repo_url, tmp)
            job.report = _run_pipeline(tmp, job.repo)
        job.status = "done"
        log.info("job done job_id=%s repo=%s", job.id, job.repo)
    except JobFailed as exc:
        job.status = "error"
        job.error = {"code": exc.code, "message": exc.message}
        log.info(
            "job error job_id=%s repo=%s code=%s", job.id, job.repo, exc.code
        )
    except Exception:
        log.exception("job crashed job_id=%s repo=%s", job.id, job.repo)
        job.status = "error"
        job.error = {
            "code": "analysis_failed",
            "message": "analysis failed unexpectedly",
        }
    finally:
        job.finished_at = datetime.now(timezone.utc)
