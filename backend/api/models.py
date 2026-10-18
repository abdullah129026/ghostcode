"""Pydantic contracts for the GhostCode HTTP API.

Every input the API accepts goes through these models. The report
payload itself is the versioned dict built by engines.report (schema 1);
it passes through untouched so the CLI and the API serve byte-identical
contracts to the dashboard.
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


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
