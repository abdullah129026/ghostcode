import json
import os

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


def test_run_tests_no_suite(tmp_path):
    with pytest.raises(SandboxError) as exc:
        run_tests(str(tmp_path))
    assert exc.value.code == "no_test_suite"
