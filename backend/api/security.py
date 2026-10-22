"""Trust boundaries for the public API: URL validation and rate limiting.

The only thing the API ever clones is a public github.com repo over
https. Anything else is rejected before git is invoked. Rate limiting
is stdlib-only on purpose: a token bucket needs a clock and a counter,
not a dependency.
"""

import logging
import os
import re
import threading
import time
from urllib.parse import urlparse

log = logging.getLogger("ghostcode.security")

_OWNER_REPO = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.-]*")


class RepoURLError(ValueError):
    """Rejected repo_url; carries the API-facing error code."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_repo_url(raw) -> str:
    """Return the canonical clone URL for a v1-acceptable repo URL.

    Accepts only ``https://github.com/<owner>/<repo>`` (a ``.git`` suffix
    and a trailing slash are tolerated). Rejects embedded credentials,
    non-github hosts, ssh-style URLs, and anything that is not exactly
    owner/repo. The returned URL never contains credentials by
    construction, so it is safe to log.
    """
    if not isinstance(raw, str):
        raise RepoURLError("invalid_repo_url", "repo_url must be a string")
    try:
        parts = urlparse(raw.strip())
        host = parts.hostname or ""
        userinfo = parts.username or parts.password
    except ValueError:
        raise RepoURLError("invalid_repo_url", "repo_url is not a valid URL")
    if parts.scheme != "https":
        raise RepoURLError("invalid_repo_url", "repo_url must be an https URL")
    if host != "github.com":
        raise RepoURLError(
            "invalid_repo_url", "v1 only analyzes public repos on github.com"
        )
    if userinfo:
        raise RepoURLError(
            "credentials_in_url", "never put credentials in repo_url"
        )
    if parts.query or parts.fragment:
        raise RepoURLError(
            "invalid_repo_url", "repo_url must be a plain owner/repo path"
        )
    path = parts.path.strip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    segments = path.split("/")
    if len(segments) != 2 or not all(
        _OWNER_REPO.fullmatch(s) for s in segments
    ):
        raise RepoURLError(
            "invalid_repo_url",
            "repo_url must look like https://github.com/<owner>/<repo>",
        )
    owner, repo = segments
    return f"https://github.com/{owner}/{repo}.git"


def repo_label(canonical_url: str) -> str:
    """Human- and log-safe label for a validated URL: ``owner/repo``."""
    path = urlparse(canonical_url).path
    if path.endswith(".git"):
        path = path[: -len(".git")]
    return path.strip("/")


class RateLimiter:
    """Per-key token bucket. In-memory and per-process by design.

    # ponytail: one uvicorn worker in v1, so a single bucket map holds;
    # move to Redis when workers scale past one.
    """

    _MAX_KEYS = 10_000

    def __init__(self, per_minute: float, burst: int):
        self._rate = per_minute / 60.0
        self._burst = burst
        self._buckets: dict = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        with self._lock:
            if len(self._buckets) > self._MAX_KEYS:
                # shed the stalest quarter: cheap insurance against
                # unbounded growth from a spray of distinct IPs.
                ordered = sorted(
                    self._buckets.items(), key=lambda kv: kv[1][1]
                )
                for stale, _ in ordered[: self._MAX_KEYS // 4]:
                    del self._buckets[stale]
            tokens, updated = self._buckets.get(key, (self._burst, now))
            tokens = min(self._burst, tokens + (now - updated) * self._rate)
            if tokens >= 1:
                self._buckets[key] = (tokens - 1, now)
                return True, 0.0
            retry_after = (1 - tokens) / self._rate
            self._buckets[key] = (tokens, now)
            return False, retry_after


def _env_number(name: str, default, parse):
    """Read a numeric env var, falling back to default on garbage.

    A mistyped operator setting used to raise ValueError at import time
    and take the whole service down; now it logs a warning and uses
    the default.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return parse(raw)
    except (TypeError, ValueError):
        log.warning("invalid %s=%r, using default %s", name, raw, default)
        return default


def env_float(name: str, default: float) -> float:
    return _env_number(name, default, float)


def env_int(name: str, default: int) -> int:
    return _env_number(name, default, int)


def limiter_from_env(
    prefix: str, default_per_minute: float, default_burst: int
) -> RateLimiter:
    return RateLimiter(
        per_minute=env_float(f"{prefix}_PER_MIN", default_per_minute),
        burst=env_int(f"{prefix}_BURST", default_burst),
    )
