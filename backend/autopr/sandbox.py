"""Sandboxed test runs: the gate an auto-PR never skips.

Untrusted repo code runs here, so this module is paranoid on purpose:

- fresh scrubbed environment: only PATH, HOME (a throwaway dir), LANG,
  CI and a few build-tool flags survive. Every *TOKEN*, *SECRET*,
  *KEY* and GHOSTCODE_* variable is gone by construction.
- resource limits via setrlimit: CPU time, address space, max file
  size, process count. A fork bomb or a memory hog dies in the child,
  not on the host.
- no shell, argv only, cwd pinned to the clone, wall-clock timeout on
  every command.
- the API never sees raw test output (assertion diffs can contain
  source lines); it gets a one-line verdict, counts only.

Known residual risk, stated plainly: the sandbox does not isolate the
network (no netns without privileges on the free tier), so dependency
installs and test runs can reach the internet. The upgrade path is a
real container boundary (Docker/gVisor) when the project outgrows $0.
See docs/adr/0001-auto-pr-sandbox.md.
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile

from api.security import env_int

log = logging.getLogger("ghostcode.autopr.sandbox")

# ponytail: reuse api.security.env_int (stdlib-only, no import cycle):
# a mistyped operator value used to raise ValueError at import and take
# the whole API down at boot; now it logs a warning and uses the default.
SANDBOX_TIMEOUT = env_int("GHOSTCODE_SANDBOX_TIMEOUT", 600)
SANDBOX_MEM_MB = env_int("GHOSTCODE_SANDBOX_MEM_MB", 2048)
LOG_TAIL_LINES = 40

_PYTEST_MARKERS = (
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "pyproject.toml",
    "tests",
    "test",
)
_PY_REQUIREMENTS = (
    "requirements.txt",
    "requirements-test.txt",
    "requirements_test.txt",
    "dev-requirements.txt",
)
_PASSED_RE = re.compile(r"(\d+)\s+passed")


class SandboxError(Exception):
    """A sandbox failure, with an API-facing code and message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _wanted_runner(root: str) -> str | None:
    """Which test runner the repo looks like it wants, config-only."""
    if any(os.path.exists(os.path.join(root, m)) for m in _PYTEST_MARKERS):
        return "pytest"
    pkg = os.path.join(root, "package.json")
    if os.path.exists(pkg):
        return "npm"
    return None


def detect_runner(root: str) -> str | None:
    """Runner name whose config exists AND whose binary is on PATH."""
    wanted = _wanted_runner(root)
    if wanted == "pytest" and shutil.which(sys.executable):
        return "pytest"
    if wanted == "npm" and shutil.which("npm"):
        return "npm"
    return None


def _child_limits():
    """preexec_fn: clamp the child before it execs. Fail closed."""
    def _inner():
        import resource

        try:
            resource.setrlimit(
                resource.RLIMIT_CPU, (SANDBOX_TIMEOUT, SANDBOX_TIMEOUT + 30)
            )
            mem = SANDBOX_MEM_MB * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (mem, mem))
            resource.setrlimit(
                resource.RLIMIT_FSIZE, (512 * 1024 * 1024, 512 * 1024 * 1024)
            )
            if hasattr(resource, "RLIMIT_NPROC"):
                resource.setrlimit(resource.RLIMIT_NPROC, (256, 256))
        except (OSError, ValueError) as exc:
            os.write(2, f"sandbox limits failed: {exc}\n".encode())
            os._exit(127)

    return _inner


def _scrubbed_env(home: str) -> dict:
    # ponytail: build the env from scratch instead of filtering
    # os.environ; allowlisting beats denylisting for secrets.
    return {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": home,
        "LANG": "C.UTF-8",
        "CI": "true",
        "GIT_TERMINAL_PROMPT": "0",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "NPM_CONFIG_AUDIT": "false",
        "NPM_CONFIG_FUND": "false",
    }


def _run(argv: list, root: str, env: dict, timeout: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv,
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        preexec_fn=_child_limits(),
    )


def _tail(proc: subprocess.CompletedProcess) -> str:
    out = (proc.stdout or "") + (proc.stderr or "")
    return "\n".join(out.splitlines()[-LOG_TAIL_LINES:])


def _install_deps(root: str, runner: str, env: dict) -> None:
    """Best-effort dependency install inside the sandbox.

    A repo whose deps cannot install cannot produce a trustworthy
    green run, so an install failure fails the gate instead of being
    skipped over.
    """
    if runner == "pytest":
        reqs = [
            os.path.join(root, name)
            for name in _PY_REQUIREMENTS
            if os.path.exists(os.path.join(root, name))
        ]
        for req in reqs:
            proc = _run(
                [sys.executable, "-m", "pip", "install", "-r", req],
                root,
                env,
                SANDBOX_TIMEOUT,
            )
            if proc.returncode != 0:
                raise SandboxError(
                    "deps_install_failed",
                    f"pip install failed for {os.path.basename(req)}",
                )
    else:
        lock = os.path.join(root, "package-lock.json")
        argv = (
            ["npm", "ci", "--no-audit", "--no-fund"]
            if os.path.exists(lock)
            else ["npm", "install", "--no-audit", "--no-fund"]
        )
        proc = _run(argv, root, env, SANDBOX_TIMEOUT)
        if proc.returncode != 0:
            raise SandboxError("deps_install_failed", "npm install failed")


def _summarize(runner: str, proc: subprocess.CompletedProcess) -> str:
    match = _PASSED_RE.search(proc.stdout or "")
    if match:
        return f"{runner}: {match.group(1)} passed"
    return f"{runner}: exit code {proc.returncode}"


def run_tests(root: str) -> tuple[bool, str, str]:
    """Run the repo's test suite in the sandbox.

    Returns (passed, summary, log_tail). summary is API-safe (counts
    only); log_tail stays server-side. Raises SandboxError when the
    gate cannot run or times out.
    """
    wanted = _wanted_runner(root)
    runner = detect_runner(root)
    if runner is None:
        if wanted == "npm":
            raise SandboxError(
                "runner_unavailable",
                "repo has a JS test script but node/npm is not installed",
            )
        raise SandboxError(
            "no_test_suite",
            "no pytest or npm test suite found; the auto-PR gate needs "
            "a runnable test suite",
        )
    home = tempfile.mkdtemp(prefix="ghostcode-sandbox-home-")
    env = _scrubbed_env(home)
    try:
        log.info("sandbox installing deps runner=%s", runner)
        _install_deps(root, runner, env)
        if runner == "pytest":
            argv = [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
            ]
        else:
            argv = ["npm", "test", "--silent"]
        log.info("sandbox running tests runner=%s", runner)
        try:
            proc = _run(argv, root, env, SANDBOX_TIMEOUT)
        except subprocess.TimeoutExpired:
            raise SandboxError(
                "tests_timeout",
                f"test suite ran longer than {SANDBOX_TIMEOUT}s",
            )
        tail = _tail(proc)
        summary = _summarize(runner, proc)
        log.info("sandbox finished runner=%s passed=%s", runner, proc.returncode == 0)
        return proc.returncode == 0, summary, tail
    finally:
        shutil.rmtree(home, ignore_errors=True)
