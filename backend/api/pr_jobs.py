"""Auto-PR jobs: select -> clone -> branch -> delete -> commit ->
sandbox tests -> push -> open the PR.

POST /pr returns 202 immediately and the work happens on a daemon
thread, same as analysis jobs. The GitHub token arrives in the request
body and is passed into the worker thread only: it is never stored on
the job record, never logged, and every failure path redacts it. The
clone lives in a tempdir that is removed when the job settles, success
or failure.
"""

import logging
import tempfile
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from autopr import github_pr, sandbox, select

from . import jobs

log = logging.getLogger("ghostcode.pr_jobs")

MAX_PR_JOBS = 100


@dataclass
class PrJob:
    id: str
    analysis_job_id: str
    repo: str  # "owner/repo", safe for logs and the UI
    files: list = field(default_factory=list)  # validated report paths
    status: str = "queued"
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: datetime | None = None
    finished_at: datetime | None = None
    pr_url: str | None = None
    test_summary: str | None = None  # API-safe one-liner, counts only
    error: dict | None = None


class PrStore:
    """Thread-safe in-memory PR-job registry, oldest-first eviction."""

    def __init__(self, max_jobs: int = MAX_PR_JOBS):
        self._jobs: dict[str, PrJob] = {}
        self._lock = threading.Lock()
        self._max_jobs = max_jobs

    def create(self, analysis_job_id: str, repo: str, files: list) -> PrJob:
        job = PrJob(
            id=uuid.uuid4().hex,
            analysis_job_id=analysis_job_id,
            repo=repo,
            files=[g["path"] for g in files],
        )
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > self._max_jobs:
                oldest = min(self._jobs.values(), key=lambda j: j.created_at)
                del self._jobs[oldest.id]
        return job

    def get(self, pr_job_id: str) -> PrJob | None:
        with self._lock:
            return self._jobs.get(pr_job_id)


def _fail(job: PrJob, code: str, message: str) -> None:
    job.status = "error"
    job.error = {"code": code, "message": message}
    log.info(
        "pr job error pr_job_id=%s repo=%s code=%s",
        job.id,
        job.repo,
        code,
    )


def run_pr_job(
    pr_store: PrStore,
    pr_job_id: str,
    job_store: jobs.JobStore,
    analysis_job_id: str,
    token: str,
    requested: list | None,
) -> None:
    """Worker entrypoint: settle one PR job. Never raises, never leaks."""
    job = pr_store.get(pr_job_id)
    if job is None:
        return
    job.status = "running"
    job.started_at = datetime.now(timezone.utc)
    log.info(
        "pr job started pr_job_id=%s repo=%s files=%d",
        job.id,
        job.repo,
        len(job.files),
    )
    try:
        analysis = job_store.get(analysis_job_id)
        if analysis is None or analysis.status != "done":
            raise select.SelectionError(
                "report_not_ready", "the analysis report is not ready"
            )
        selected = select.select_files(analysis.report, requested)
        branch = f"ghostcode/safe-delete-{job.id[:8]}"
        authed = github_pr.authed_clone_url(analysis.repo_url, token)
        with tempfile.TemporaryDirectory(prefix="ghostcode-pr-") as tmp:
            github_pr.clone_repo(analysis.repo_url, token, tmp)
            github_pr.create_delete_commit(tmp, selected, branch)
            passed, summary, _tail = sandbox.run_tests(tmp)
            job.test_summary = summary
            if not passed:
                raise sandbox.SandboxError(
                    "tests_failed",
                    f"sandbox: {summary}, the PR was not opened",
                )
            github_pr.push_branch(tmp, branch, authed, token)
        job.pr_url = github_pr.open_pull_request(
            token, analysis.repo, branch, selected, summary
        )
        job.status = "done"
        log.info(
            "pr job done pr_job_id=%s repo=%s pr_url=%s",
            job.id,
            job.repo,
            job.pr_url,
        )
    except (
        select.SelectionError,
        github_pr.GitError,
        github_pr.PrError,
        sandbox.SandboxError,
    ) as exc:
        _fail(job, exc.code, exc.message)
    except Exception:
        log.exception("pr job crashed pr_job_id=%s repo=%s", job.id, job.repo)
        _fail(job, "pr_failed", "the auto-PR run failed unexpectedly")
    finally:
        job.finished_at = datetime.now(timezone.utc)
