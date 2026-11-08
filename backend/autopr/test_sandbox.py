import json
import os
import subprocess

import pytest

from autopr import sandbox
from autopr.sandbox import SandboxError, detect_runner, run_tests


def _fixture_repo(root, failing=False):
    os.makedirs(os.path.join(root, "pkg"))
    with open(os.path.join(root, "pkg", "__init__.py"), "w") as f:
        f.write("")
    with open(os.path.join(root, "pkg", "live.py"), "w") as f:
        f.write("def add(a, b):\n    return a + b\n")
    with open(os.path.join(root, "pkg", "dead.py"), "w") as f:
        f.write("def unused():\n    return 1\n")
    os.makedirs(os.path.join(root, "tests"))
    body = "def test_add():\n    from pkg.live import add\n    assert add(1, 2) == 3\n"
    if failing:
        body += "\ndef test_broken():\n    assert 1 == 2\n"
    # the scrubbed env must not leak the parent process's secrets
    body += (
        "\ndef test_no_secret_leak():\n"
        "    import os\n"
        "    assert 'GHOSTCODE_TEST_SECRET' not in os.environ\n"
    )
    with open(os.path.join(root, "tests", "test_live.py"), "w") as f:
        f.write(body)


def test_detect_runner_pytest(tmp_path):
    _fixture_repo(str(tmp_path))
    assert detect_runner(str(tmp_path)) == "pytest"


def test_detect_runner_none_for_empty_dir(tmp_path):
    assert detect_runner(str(tmp_path)) is None


def test_detect_runner_npm_when_binary_present(tmp_path, monkeypatch):
    pkg = {"name": "x", "scripts": {"test": "jest"}}
    with open(tmp_path / "package.json", "w") as f:
        json.dump(pkg, f)
    # wanted is npm and the binary is on PATH: the npm gate is the answer
    monkeypatch.setattr(
        sandbox.shutil, "which", lambda name: "/usr/bin/npm" if name == "npm" else None
    )
    assert detect_runner(str(tmp_path)) == "npm"


def test_detect_runner_npm_config_only(tmp_path):
    pkg = {"name": "x", "scripts": {"test": "jest"}}
    with open(tmp_path / "package.json", "w") as f:
        json.dump(pkg, f)
    # wanted is npm; binary presence decides the final answer
    assert sandbox._wanted_runner(str(tmp_path)) == "npm"


def test_run_tests_green(tmp_path, monkeypatch):
    monkeypatch.setenv("GHOSTCODE_TEST_SECRET", "shh")
    monkeypatch.setattr(sandbox, "SANDBOX_TIMEOUT", 120)
    _fixture_repo(str(tmp_path))
    passed, summary, tail = run_tests(str(tmp_path))
    assert passed is True
    assert "passed" in summary
    # raw output stays server-side: the summary is counts only
    assert "shh" not in summary


def test_run_tests_red(tmp_path, monkeypatch):
    monkeypatch.setattr(sandbox, "SANDBOX_TIMEOUT", 120)
    _fixture_repo(str(tmp_path), failing=True)
    passed, summary, _tail = run_tests(str(tmp_path))
    assert passed is False
    assert "exit code" in summary or "passed" in summary


def test_install_deps_failure_fails_the_gate(tmp_path, monkeypatch):
    # The pip-install branch of _install_deps was the only untested
    # branch in the gate: a repo whose deps cannot install must fail
    # the gate, never silently run against missing deps.
    (tmp_path / "requirements.txt").write_text("no-such-package-xyz\n")
    monkeypatch.setattr(
        sandbox,
        "_run",
        lambda argv, root, env, timeout: subprocess.CompletedProcess(
            argv, 1, stdout="", stderr="ERROR: no matching distribution"
        ),
    )
    with pytest.raises(SandboxError) as exc:
        sandbox._install_deps(str(tmp_path), "pytest", {})
    assert exc.value.code == "deps_install_failed"


def test_install_deps_timeout_fails_the_gate(tmp_path, monkeypatch):
    # A dependency install that hangs past SANDBOX_TIMEOUT used to raise
    # raw subprocess.TimeoutExpired out of run_tests, so the PR job
    # landed on the generic "pr_failed" code instead of a precise
    # deps_install_failed verdict. Both runners share the install path.
    (tmp_path / "requirements.txt").write_text("requests\n")
    (tmp_path / "package.json").write_text('{"name": "x"}')

    def _hang(argv, root, env, timeout):
        raise subprocess.TimeoutExpired(argv, timeout)

    monkeypatch.setattr(sandbox, "_run", _hang)
    for runner in ("pytest", "npm"):
        with pytest.raises(SandboxError) as exc:
            sandbox._install_deps(str(tmp_path), runner, {})
        assert exc.value.code == "deps_install_failed"
        assert "timed out" in exc.value.message


def test_install_deps_npm_failure_fails_the_gate(tmp_path, monkeypatch):
    # Mirror of the pip-install branch: a repo whose npm deps cannot
    # install must fail the gate, never silently run against missing deps.
    (tmp_path / "package.json").write_text('{"name": "x"}')
    monkeypatch.setattr(
        sandbox,
        "_run",
        lambda argv, root, env, timeout: subprocess.CompletedProcess(
            argv, 1, stdout="", stderr="npm ERR! 404 Not Found"
        ),
    )
    with pytest.raises(SandboxError) as exc:
        sandbox._install_deps(str(tmp_path), "npm", {})
    assert exc.value.code == "deps_install_failed"


def test_run_tests_npm_green(tmp_path, monkeypatch):
    # The npm gate had zero coverage: pin the install + test argv path
    # end to end (npm install, then npm test) without needing a real node.
    pkg = {"name": "x", "scripts": {"test": "jest"}}
    with open(tmp_path / "package.json", "w") as f:
        json.dump(pkg, f)
    monkeypatch.setattr(sandbox, "detect_runner", lambda root: "npm")
    monkeypatch.setattr(sandbox, "SANDBOX_TIMEOUT", 120)

    def _fake_run(argv, root, env, timeout):
        if argv[1] in ("ci", "install"):
            return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(
            argv, 0, stdout="3 passed\n", stderr="")

    monkeypatch.setattr(sandbox, "_run", _fake_run)
    passed, summary, _tail = run_tests(str(tmp_path))
    assert passed is True
    assert summary == "npm: 3 passed"


def test_run_tests_no_suite(tmp_path):
    with pytest.raises(SandboxError) as exc:
        run_tests(str(tmp_path))
    assert exc.value.code == "no_test_suite"


def test_summarize_falls_back_to_exit_code_without_pass_count():
    # A run whose output has no "N passed" line (collection error, crash
    # before any test ran) still needs a summary: the exit code, not a
    # crash in the summarizer.
    proc = subprocess.CompletedProcess(
        ["pytest"], 1, stdout="ERROR: collection failed\n", stderr=""
    )
    assert sandbox._summarize("pytest", proc) == "pytest: exit code 1"


def test_run_tests_runner_unavailable_when_npm_missing(tmp_path, monkeypatch):
    # A JS repo on a host without node/npm must get the precise
    # runner_unavailable code, not the generic no_test_suite one: the
    # suite exists, the binary does not.
    (tmp_path / "package.json").write_text('{"name": "x"}')
    monkeypatch.setattr(sandbox.shutil, "which", lambda name: None)
    with pytest.raises(SandboxError) as exc:
        run_tests(str(tmp_path))
    assert exc.value.code == "runner_unavailable"


def test_run_tests_timeout_fails_the_gate(tmp_path, monkeypatch):
    # A test suite that runs past SANDBOX_TIMEOUT must surface as
    # tests_timeout, the same precise verdict the install path already
    # has, instead of raw TimeoutExpired escaping run_tests.
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_live.py").write_text(
        "def test_ok():\n    assert True\n"
    )
    monkeypatch.setattr(sandbox, "SANDBOX_TIMEOUT", 120)

    def _hang(argv, root, env, timeout):
        raise subprocess.TimeoutExpired(argv, timeout)

    monkeypatch.setattr(sandbox, "_run", _hang)
    with pytest.raises(SandboxError) as exc:
        run_tests(str(tmp_path))
    assert exc.value.code == "tests_timeout"


def test_sandbox_env_caps_fall_back_and_read(monkeypatch):
    """Garbage GHOSTCODE_SANDBOX_* must not crash the import (cf. api
    env tolerance, commit 3cc9d09, which missed this module). Reloading
    re-reads the env; the last block restores the pristine defaults so
    later tests see the same constants a fresh import would."""
    import importlib

    from autopr import sandbox as sb

    monkeypatch.setenv("GHOSTCODE_SANDBOX_TIMEOUT", "abc")
    monkeypatch.setenv("GHOSTCODE_SANDBOX_MEM_MB", "")
    importlib.reload(sb)
    assert (sb.SANDBOX_TIMEOUT, sb.SANDBOX_MEM_MB) == (600, 2048)
    monkeypatch.setenv("GHOSTCODE_SANDBOX_TIMEOUT", "30")
    monkeypatch.setenv("GHOSTCODE_SANDBOX_MEM_MB", "512")
    importlib.reload(sb)
    assert (sb.SANDBOX_TIMEOUT, sb.SANDBOX_MEM_MB) == (30, 512)
    monkeypatch.setenv("GHOSTCODE_SANDBOX_TIMEOUT", "600")
    monkeypatch.setenv("GHOSTCODE_SANDBOX_MEM_MB", "2048")
    importlib.reload(sb)
    assert (sb.SANDBOX_TIMEOUT, sb.SANDBOX_MEM_MB) == (600, 2048)
