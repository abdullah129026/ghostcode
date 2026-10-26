"""Security tests: the URL allowlist is the money boundary.

A validator that lets a credential-bearing or off-host URL through
would hand git an attacker-controlled remote, so every rejection shape
is pinned here.
"""

import pytest

from api.security import (
    RateLimiter,
    RepoURLError,
    repo_label,
    validate_repo_url,
)


@pytest.mark.parametrize(
    "raw, canonical",
    [
        ("https://github.com/acme/widgets", "https://github.com/acme/widgets.git"),
        ("https://github.com/acme/widgets.git", "https://github.com/acme/widgets.git"),
        ("https://github.com/acme/widgets/", "https://github.com/acme/widgets.git"),
        ("https://github.com/Acme/Widgets.JS", "https://github.com/Acme/Widgets.JS.git"),
        ("https://github.com/a-b_c/d.e-f_g", "https://github.com/a-b_c/d.e-f_g.git"),
        ("  https://github.com/acme/widgets  ", "https://github.com/acme/widgets.git"),
    ],
)
def test_valid_urls_canonicalize(raw, canonical):
    assert validate_repo_url(raw) == canonical


@pytest.mark.parametrize(
    "raw, code",
    [
        ("http://github.com/acme/widgets", "invalid_repo_url"),
        ("git@github.com:acme/widgets.git", "invalid_repo_url"),
        ("ssh://git@github.com/acme/widgets", "invalid_repo_url"),
        ("https://gitlab.com/acme/widgets", "invalid_repo_url"),
        ("https://evilgithub.com/acme/widgets", "invalid_repo_url"),
        ("https://github.com.evil.com/acme/widgets", "invalid_repo_url"),
        ("https://user:token123@github.com/acme/widgets", "credentials_in_url"),
        ("https://user@github.com/acme/widgets", "credentials_in_url"),
        ("https://github.com/acme", "invalid_repo_url"),
        ("https://github.com/acme/widgets/extra", "invalid_repo_url"),
        ("https://github.com//widgets", "invalid_repo_url"),
        ("https://github.com/acme/widgets?tab=readme", "invalid_repo_url"),
        ("https://github.com/acme/widgets#readme", "invalid_repo_url"),
        ("https://github.com/acme/with space", "invalid_repo_url"),
        ("not a url", "invalid_repo_url"),
        ("", "invalid_repo_url"),
        (None, "invalid_repo_url"),
        (123, "invalid_repo_url"),
    ],
)
def test_invalid_urls_rejected_with_codes(raw, code):
    with pytest.raises(RepoURLError) as exc_info:
        validate_repo_url(raw)
    assert exc_info.value.code == code


def test_repo_label_is_log_safe():
    assert repo_label("https://github.com/acme/widgets.git") == "acme/widgets"


def test_limiter_allows_burst_then_denies():
    limiter = RateLimiter(per_minute=60, burst=2)
    assert limiter.allow("1.2.3.4") == (True, 0.0)
    assert limiter.allow("1.2.3.4")[0] is True
    allowed, retry_after = limiter.allow("1.2.3.4")
    assert allowed is False
    assert retry_after > 0


def test_limiter_with_zero_rate_denies_without_crashing():
    limiter = RateLimiter(per_minute=0, burst=1)
    assert limiter.allow("1.2.3.4")[0] is True
    allowed, retry_after = limiter.allow("1.2.3.4")
    assert allowed is False
    assert retry_after > 0


def test_limiter_is_per_key():
    limiter = RateLimiter(per_minute=60, burst=1)
    limiter.allow("1.2.3.4")
    assert limiter.allow("5.6.7.8")[0] is True


def test_limiter_refills_over_time(monkeypatch):
    limiter = RateLimiter(per_minute=60, burst=1)
    now = [1000.0]
    monkeypatch.setattr("api.security.time.monotonic", lambda: now[0])
    assert limiter.allow("1.2.3.4")[0] is True
    assert limiter.allow("1.2.3.4")[0] is False
    now[0] += 61.0
    assert limiter.allow("1.2.3.4")[0] is True


def test_limiter_from_env_uses_defaults_when_unset(monkeypatch):
    from api.security import limiter_from_env

    monkeypatch.delenv("GHOSTCODE_ANALYZE_RATE_PER_MIN", raising=False)
    monkeypatch.delenv("GHOSTCODE_ANALYZE_RATE_BURST", raising=False)
    limiter = limiter_from_env("GHOSTCODE_ANALYZE_RATE", 20, 5)
    assert limiter._burst == 5
    assert sum(limiter.allow("1.2.3.4")[0] for _ in range(6)) == 5


def test_limiter_from_env_falls_back_on_garbage(monkeypatch):
    from api.security import limiter_from_env

    monkeypatch.setenv("GHOSTCODE_ANALYZE_RATE_PER_MIN", "abc")
    monkeypatch.setenv("GHOSTCODE_ANALYZE_RATE_BURST", "")
    limiter = limiter_from_env("GHOSTCODE_ANALYZE_RATE", 20, 5)
    assert limiter._burst == 5
    assert sum(limiter.allow("1.2.3.4")[0] for _ in range(6)) == 5


def test_limiter_from_env_reads_valid_values(monkeypatch):
    from api.security import limiter_from_env

    monkeypatch.setenv("GHOSTCODE_ANALYZE_RATE_PER_MIN", "60")
    monkeypatch.setenv("GHOSTCODE_ANALYZE_RATE_BURST", "2")
    limiter = limiter_from_env("GHOSTCODE_ANALYZE_RATE", 20, 5)
    assert limiter._burst == 2
    assert sum(limiter.allow("1.2.3.4")[0] for _ in range(3)) == 2
