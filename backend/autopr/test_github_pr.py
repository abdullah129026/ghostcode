import os
import subprocess

import pytest

from autopr import github_pr
from autopr.github_pr import (
    GitError,
    PrError,
    _clone,
    authed_clone_url,
    create_delete_commit,
    open_pull_request,
    pr_body,
    push_branch,
    redact,
)

TOKEN = "ghp_testtoken123"


def _git(args, cwd):
    subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    )


@pytest.fixture()
def origin(tmp_path):
    """A local bare repo playing the role of github.com."""
    bare = tmp_path / "origin.git"
    _git(["init", "--bare", str(bare)], cwd=str(tmp_path))
    work = tmp_path / "work"
    work.mkdir()
    _git(["init"], cwd=str(work))
    _git(["config", "user.email", "t@t.t"], cwd=str(work))
    _git(["config", "user.name", "t"], cwd=str(work))
    (work / "live.py").write_text("X = 1\n")
    (work / "dead.py").write_text("Y = 2\n")
    _git(["add", "-A"], cwd=str(work))
    _git(["commit", "-m", "init"], cwd=str(work))
    _git(["branch", "-M", "main"], cwd=str(work))
    _git(["remote", "add", "origin", str(bare)], cwd=str(work))
    _git(["push", "-u", "origin", "main"], cwd=str(work))
    # a real host points HEAD at the default branch; do the same
    subprocess.run(
        ["git", "--git-dir", str(bare), "symbolic-ref",
         "HEAD", "refs/heads/main"],
        check=True,
        capture_output=True,
    )
    return bare


def _refs(bare):
    out = subprocess.run(
        ["git", "--git-dir", str(bare), "show-ref"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return out


def test_clone_branch_delete_push_local(origin, tmp_path):
    dest = str(tmp_path / "clone")
    _clone(f"file://{origin}", dest)
    create_delete_commit(
        dest, [{"path": "dead.py", "loc": 1}], "ghostcode/test-1"
    )
    assert not os.path.exists(os.path.join(dest, "dead.py"))
    push_branch(dest, "ghostcode/test-1", f"file://{origin}", TOKEN)
    assert "refs/heads/ghostcode/test-1" in _refs(origin)


def test_create_delete_commit_rejects_path_escape(origin, tmp_path):
    dest = str(tmp_path / "clone")
    _clone(f"file://{origin}", dest)
    with pytest.raises(GitError) as exc:
        create_delete_commit(
            dest, [{"path": "../evil.py", "loc": 1}], "ghostcode/evil"
        )
    assert exc.value.code == "invalid_file"


def test_create_delete_commit_rejects_missing_file(origin, tmp_path):
    dest = str(tmp_path / "clone")
    _clone(f"file://{origin}", dest)
    with pytest.raises(GitError) as exc:
        create_delete_commit(
            dest, [{"path": "nope.py", "loc": 1}], "ghostcode/nope"
        )
    assert exc.value.code == "file_missing"


def test_authed_clone_url_splices_token():
    url = authed_clone_url("https://github.com/o/r.git", TOKEN)
    assert url == f"https://{TOKEN}@github.com/o/r.git"
    assert "github.com/o/r.git" in url


def test_git_errors_redact_the_token(monkeypatch):
    def boom(*a, **k):
        raise subprocess.TimeoutExpired("git", 1)

    monkeypatch.setattr(subprocess, "run", boom)
    with pytest.raises(GitError) as exc:
        github_pr._git(["clone", TOKEN], cwd="/tmp", token=TOKEN)
    assert TOKEN not in exc.value.message


class _FakePr:
    html_url = "https://github.com/o/r/pull/7"


class _FakeRepo:
    default_branch = "main"

    def create_pull(self, **kwargs):
        assert kwargs["head"] == "ghostcode/x"
        assert kwargs["base"] == "main"
        assert "dead.py" in kwargs["body"]
        return _FakePr()


class _FakeGithub:
    def __init__(self, auth=None):
        pass

    def get_repo(self, name):
        assert name == "o/r"
        return _FakeRepo()

    def close(self):
        pass


def test_open_pull_request_returns_url(monkeypatch):
    monkeypatch.setattr(github_pr, "Github", _FakeGithub)
    url = open_pull_request(
        TOKEN,
        "o/r",
        "ghostcode/x",
        [{"path": "dead.py", "loc": 12, "annual_saving_usd": 4.5,
          "reasons": ["entire file is unreferenced"]}],
        "pytest: 3 passed",
    )
    assert url == "https://github.com/o/r/pull/7"


def test_open_pull_request_wraps_failures_redacted(monkeypatch):
    class _BadGithub(_FakeGithub):
        def get_repo(self, name):
            raise RuntimeError(f"auth failed for {TOKEN}")

    monkeypatch.setattr(github_pr, "Github", _BadGithub)
    with pytest.raises(PrError) as exc:
        open_pull_request(TOKEN, "o/r", "ghostcode/x", [], "pytest: 1 passed")
    assert exc.value.code == "pr_failed"
    assert TOKEN not in exc.value.message


def test_pr_body_lists_files_and_safety_note():
    body = pr_body(
        [{"path": "dead.py", "loc": 12, "annual_saving_usd": 4.5,
          "reasons": ["entire file is unreferenced"]}],
        "o/r",
        "pytest: 3 passed",
    )
    assert "`dead.py`" in body
    assert "zero incoming edges" in body
    assert "pytest: 3 passed" in body
    assert "merged automatically" in body
