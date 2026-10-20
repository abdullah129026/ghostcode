"""Pydantic contracts for the GhostCode HTTP API.

Every input the API accepts goes through these models. The report
payload itself is the versioned dict built by engines.report (schema 1);
it passes through untouched so the CLI and the API serve byte-identical
contracts to the dashboard.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, SecretStr


class AnalyzeRequest(BaseModel):
    repo_url: str = Field(
        max_length=200,
        description="public https://github.com/<owner>/<repo> URL",
    )


class JobAccepted(BaseModel):
    job_id: str
    status: Literal["queued"]
    poll_url: str


class JobError(BaseModel):
    code: str
    message: str


class JobStatus(BaseModel):
    job_id: str
    status: Literal["queued", "running", "done", "error"]
    repo: str  # "owner/repo", safe for logs and the UI
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    report_url: Optional[str] = None
    error: Optional[JobError] = None


class PrRequest(BaseModel):
    job_id: str = Field(
        min_length=32,
        max_length=32,
        description="analysis job id from POST /analyze",
    )
    github_token: SecretStr = Field(
        min_length=1,
        max_length=500,
        description="GitHub PAT with repo scope; in-memory only, never stored",
    )
    files: Optional[list[str]] = Field(
        default=None,
        max_length=8,
        description="subset of the report's safe-delete files; omit for all",
    )


class PrJobAccepted(BaseModel):
    pr_job_id: str
    status: Literal["queued"]
    poll_url: str


class PrJobStatus(BaseModel):
    pr_job_id: str
    status: Literal["queued", "running", "done", "error"]
    repo: str  # "owner/repo", safe for logs and the UI
    files: list[str]
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    pr_url: Optional[str] = None
    test_summary: Optional[str] = None  # API-safe one-liner, counts only
    error: Optional[JobError] = None
