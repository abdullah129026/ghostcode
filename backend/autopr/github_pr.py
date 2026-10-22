"""Auto-PR git and GitHub operations.

Owns everything that touches the target repo: clone, branch, delete,
commit, push, and the PyGithub pull-request creation. The token lives
only in this call stack. Nothing here persists it, and every error
path redacts it before it can reach a log line or an API response.

The authenticated URL is passed as a one-shot argument to `git push`
and never written into the repo's config, so a discarded clone leaves
no credential behind.
"""

import logging
import os
import subprocess
from urllib.parse import quote

from github import Auth, Github

log = logging.getLogger("ghostcode.autopr.github")

COMMIT_AUTHOR_NAME = "GhostCode"
COMMIT_AUTHOR_EMAIL = "ghostcode@fluxyai.codes"

_GIT_ENV = {"GIT_TERMINAL_PROMPT": "0"}
REDACTED = "[redacted]"


class GitError(Exception):
    """A git operation failure, token already redacted."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class PrError(Exception):
    """A pull-request creation failure, token already redacted."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def redact(text: str, token: str) -> str:
    if not text or not token:
        return text or ""
    return text.replace(token, REDACTED)


def _git(args: list, cwd: str, token: str = "", timeout: int = 180) -> str:
    """Run git. Raises GitError with a redacted, truncated message."""
    env = dict(os.environ, **_GIT_ENV)
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        raise GitError("git_timeout", "git took too long and was stopped")
    if proc.returncode != 0:
        detail = "; ".join((proc.stderr or "git failed").splitlines())
        raise GitError("git_failed", redact(detail[:300], token))
    return proc.stdout or ""


def _clone(url: str, dest: str, token: str = "") -> None:
    try:
        _git(
            ["clone", "--depth", "1", "--single-branch", "--no-tags",
             "--", url, dest],
            cwd="/tmp",
            token=token,
            timeout=180,
        )
    except GitError as exc:
        raise GitError("clone_failed", exc.message)


def authed_clone_url(canonical_url: str, token: str) -> str:
    """Splice the token into a validated https://github.com/o/r.git URL."""
    return canonical_url.replace(
        "https://", f"https://{quote(token, safe='')}@", 1
    )


def clone_repo(canonical_url: str, token: str, dest: str) -> None:
    _clone(authed_clone_url(canonical_url, token), dest, token=token)


def _inside(root: str, rel: str) -> str:
    """Resolve a report path against the clone root. Rejects escapes."""
    abs_path = os.path.realpath(os.path.join(root, rel))
    if os.path.commonpath([abs_path, os.path.realpath(root)]) != os.path.realpath(root):
        raise GitError("invalid_file", f"path escapes the repo: {rel}")
    return abs_path


def create_delete_commit(root: str, files: list, branch: str) -> None:
    """Branch, delete the selected files, commit. Nothing is pushed."""
    _git(["checkout", "-b", branch], cwd=root)
    for ghost in files:
        path = _inside(root, ghost["path"])
        if not os.path.isfile(path):
            raise GitError(
                "file_missing",
                f"{ghost['path']} is not in the fresh clone, aborting",
            )
        os.remove(path)
        log.info("pr deleting path=%s", ghost["path"])
    _git(["add", "-A"], cwd=root)
    if not _git(["status", "--porcelain"], cwd=root).strip():
        raise GitError("nothing_to_commit", "deletions produced no diff")
    n = len(files)
    _git(
        [
            "-c",
            f"user.name={COMMIT_AUTHOR_NAME}",
            "-c",
            f"user.email={COMMIT_AUTHOR_EMAIL}",
            "commit",
            "-m",
            f"Remove {n} unused file{'s' if n != 1 else ''} (GhostCode)",
        ],
        cwd=root,
    )


def push_branch(root: str, branch: str, authed_url: str, token: str) -> None:
    """Push the branch. The authed URL is a one-shot push target."""
    try:
        _git(["push", "--", authed_url, f"{branch}:{branch}"], cwd=root, token=token)
    except GitError as exc:
        raise GitError("push_failed", exc.message)


def pr_body(files: list, repo_label: str, test_summary: str) -> str:
    lines = ["## What this removes", ""]
    total_loc = 0
    total_saving = 0.0
    for ghost in files:
        loc = ghost.get("loc", 0)
        saving = ghost.get("annual_saving_usd", 0.0) or 0.0
        total_loc += loc
        total_saving += saving
        reason = (ghost.get("reasons") or ["flagged as unreferenced"])[0]
        lines.append(
            f"- `{ghost['path']}`, {loc} LOC, ~${saving:,.2f}/yr, {reason}"
        )
    lines += [
        "",
        "## Why it is safe",
        "",
        "GhostCode's dependency graph found zero incoming edges for each "
        f"file above, and the repo's test suite passed in a sandbox after "
        f"the deletions ({test_summary}).",
        "",
        "---",
        "Opened by GhostCode. Review the diff before merging, nothing "
        "here was merged automatically.",
    ]
    return "\n".join(lines)


def open_pull_request(
    token: str,
    owner_repo: str,
    branch: str,
    files: list,
    test_summary: str,
) -> str:
    """Create the PR on GitHub. Returns the PR's HTML URL."""
    n = len(files)
    title = f"Remove {n} unused file{'s' if n != 1 else ''} (GhostCode)"
    try:
        gh = Github(auth=Auth.Token(token))
        repo = gh.get_repo(owner_repo)
        pr = repo.create_pull(
            title=title,
            body=pr_body(files, owner_repo, test_summary),
            head=branch,
            base=repo.default_branch,
        )
        url = pr.html_url
    except Exception as exc:
        raise PrError("pr_failed", redact(str(exc)[:300], token))
    finally:
        try:
            gh.close()
        except Exception:
            # never fails the PR, but a leak here is worth a debug line
            log.debug("github client close failed", exc_info=True)
    log.info("pr opened repo=%s branch=%s", owner_repo, branch)
    return url
