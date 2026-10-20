"""GhostCode HTTP API: app factory, routes, and the error envelope.

Every failure the client can see leaves here as
{"error": {"code": ..., "message": ...}}. Tracebacks and internals stay
in the server logs.
"""

import logging
import os
import re
import threading

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from autopr import select

from . import jobs, pr_jobs, security
from .models import (
    AnalyzeRequest,
    JobAccepted,
    JobStatus,
    PrJobAccepted,
    PrJobStatus,
    PrRequest,
)

log = logging.getLogger("ghostcode.api")

VERSION = "0.5.0"

_HTTP_CODES = {
    404: "not_found",
    405: "method_not_allowed",
}

_JOB_ID = re.compile(r"[0-9a-f]{32}")


class RateLimited(Exception):
    def __init__(self, retry_after: float):
        super().__init__("rate limited")
        self.retry_after = retry_after


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


def _validation_message(exc: RequestValidationError) -> str:
    bits = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(p) for p in err["loc"][1:]) or "body"
        bits.append(f"{loc}: {err['msg']}")
    return "; ".join(bits)


def create_app() -> FastAPI:
    logging.basicConfig(
        level=os.environ.get("GHOSTCODE_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    app = FastAPI(title="GhostCode API", version=VERSION)

    origins = [
        o.strip()
        for o in os.environ.get("GHOSTCODE_CORS_ORIGINS", "*").split(",")
        if o.strip()
    ]
    # ponytail: the API is public and stateless with no auth, so * is fine;
    # pin to the dashboard origin if abuse ever shows up.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_body("invalid_request", _validation_message(exc)),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException):
        code = _HTTP_CODES.get(exc.status_code, "http_error")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_body(code, str(exc.detail)),
        )

    @app.exception_handler(security.RepoURLError)
    async def repo_url_handler(request: Request, exc: security.RepoURLError):
        return JSONResponse(
            status_code=422, content=error_body(exc.code, exc.message)
        )

    @app.exception_handler(RateLimited)
    async def rate_limited_handler(request: Request, exc: RateLimited):
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(max(1, int(exc.retry_after)))},
            content=error_body("rate_limited", "too many requests, slow down"),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        log.exception("unhandled error path=%s", request.url.path)
        return JSONResponse(
            status_code=500,
            content=error_body("internal_error", "something went wrong"),
        )

    app.state.jobs = jobs.JobStore()
    app.state.pr_jobs = pr_jobs.PrStore()
    app.state.analyze_limiter = security.limiter_from_env(
        "GHOSTCODE_ANALYZE_RATE", 20, 5
    )
    app.state.read_limiter = security.limiter_from_env(
        "GHOSTCODE_READ_RATE", 120, 30
    )

    @app.get("/health")
    def health():
        return {"ok": True, "service": "ghostcode-api", "version": VERSION}

    @app.post(
        "/analyze",
        status_code=202,
        response_model=JobAccepted,
        dependencies=[Depends(_limit_analyze)],
    )
    def analyze_repo(body: AnalyzeRequest, request: Request):
        canonical = security.validate_repo_url(body.repo_url)
        store: jobs.JobStore = request.app.state.jobs
        job = store.create(canonical)
        threading.Thread(
            target=jobs.run_job, args=(store, job.id), daemon=True
        ).start()
        log.info("analyze accepted job_id=%s repo=%s", job.id, job.repo)
        return JobAccepted(
            job_id=job.id, status="queued", poll_url=f"/jobs/{job.id}"
        )

    @app.get(
        "/jobs/{job_id}",
        response_model=JobStatus,
        dependencies=[Depends(_limit_read)],
    )
    def job_status(job_id: str, request: Request):
        job = _job_or_404(request.app.state.jobs, job_id)
        return JobStatus(
            job_id=job.id,
            status=job.status,
            repo=job.repo,
            created_at=job.created_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            report_url=f"/report/{job.id}" if job.status == "done" else None,
            error=job.error,
        )

    @app.post(
        "/pr",
        status_code=202,
        response_model=PrJobAccepted,
        dependencies=[Depends(_limit_analyze)],
    )
    def open_pr(body: PrRequest, request: Request):
        # the token only ever leaves this function inside the worker
        # thread's arguments; it is never stored, logged, or echoed.
        store: jobs.JobStore = request.app.state.jobs
        job = _job_or_404(store, body.job_id)
        if job.status != "done":
            code = "not_ready" if job.status in ("queued", "running") else "report_failed"
            return JSONResponse(
                status_code=409 if code == "not_ready" else 422,
                content=error_body(code, f"analysis is {job.status}"),
            )
        try:
            selected = select.select_files(job.report, body.files)
        except select.SelectionError as exc:
            return JSONResponse(
                status_code=422, content=error_body(exc.code, exc.message)
            )
        pr_store: pr_jobs.PrStore = request.app.state.pr_jobs
        pr_job = pr_store.create(job.id, job.repo, selected)
        threading.Thread(
            target=pr_jobs.run_pr_job,
            args=(
                pr_store,
                pr_job.id,
                store,
                job.id,
                body.github_token.get_secret_value(),
                body.files,
            ),
            daemon=True,
        ).start()
        log.info(
            "pr accepted pr_job_id=%s repo=%s files=%d",
            pr_job.id,
            pr_job.repo,
            len(selected),
        )
        return PrJobAccepted(
            pr_job_id=pr_job.id, status="queued", poll_url=f"/pr-jobs/{pr_job.id}"
        )

    @app.get(
        "/pr-jobs/{pr_job_id}",
        response_model=PrJobStatus,
        dependencies=[Depends(_limit_read)],
    )
    def pr_job_status(pr_job_id: str, request: Request):
        pr_job = _job_or_404(request.app.state.pr_jobs, pr_job_id)
        return PrJobStatus(
            pr_job_id=pr_job.id,
            status=pr_job.status,
            repo=pr_job.repo,
            files=pr_job.files,
            created_at=pr_job.created_at,
            started_at=pr_job.started_at,
            finished_at=pr_job.finished_at,
            pr_url=pr_job.pr_url,
            test_summary=pr_job.test_summary,
            error=pr_job.error,
        )

    @app.get("/report/{job_id}", dependencies=[Depends(_limit_read)])
    def report(job_id: str, request: Request):
        job = _job_or_404(request.app.state.jobs, job_id)
        if job.status == "done":
            return job.report
        if job.status == "error":
            err = job.error or {
                "code": "analysis_failed",
                "message": "analysis failed",
            }
            return JSONResponse(
                status_code=422,
                content=error_body(err["code"], err["message"]),
            )
        return JSONResponse(
            status_code=409,
            content=error_body(
                "not_ready", f"analysis is {job.status}, poll /jobs/{job.id}"
            ),
        )

    return app


def _client_ip(request: Request) -> str:
    # ponytail: Render terminates TLS in front of us, so client.host is the
    # edge IP; good enough for abuse throttling, not for identity.
    return request.client.host if request.client else "unknown"


def _limit_analyze(request: Request):
    ok, retry = request.app.state.analyze_limiter.allow(_client_ip(request))
    if not ok:
        raise RateLimited(retry)


def _limit_read(request: Request):
    ok, retry = request.app.state.read_limiter.allow(_client_ip(request))
    if not ok:
        raise RateLimited(retry)


def _job_or_404(store: jobs.JobStore, job_id: str) -> jobs.Job:
    if not _JOB_ID.fullmatch(job_id or ""):
        raise StarletteHTTPException(status_code=404, detail="Not Found")
    job = store.get(job_id)
    if job is None:
        raise StarletteHTTPException(status_code=404, detail="Not Found")
    return job


app = create_app()
