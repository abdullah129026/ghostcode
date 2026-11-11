"""Walk env caps: garbage GHOSTCODE_MAX_* must fall back to defaults.

Same gap as the sandbox caps: commit 3cc9d09 made the api package
tolerate mistyped numeric env vars at import, but ingest/walk.py still
crashed the whole service at boot on a bad value. Reloading re-reads
the env; the last block restores the pristine defaults so later tests
see the same constants a fresh import would.
"""

import importlib

import pytest

from ingest import walk


def test_walk_env_caps_fall_back_and_read(monkeypatch):
    monkeypatch.setenv("GHOSTCODE_MAX_FILES", "abc")
    monkeypatch.setenv("GHOSTCODE_MAX_FILE_BYTES", "")
    importlib.reload(walk)
    assert (walk.MAX_FILES, walk.MAX_FILE_BYTES) == (20000, 1000000)
    monkeypatch.setenv("GHOSTCODE_MAX_FILES", "500")
    monkeypatch.setenv("GHOSTCODE_MAX_FILE_BYTES", "2048")
    importlib.reload(walk)
    assert (walk.MAX_FILES, walk.MAX_FILE_BYTES) == (500, 2048)
    monkeypatch.setenv("GHOSTCODE_MAX_FILES", "20000")
    monkeypatch.setenv("GHOSTCODE_MAX_FILE_BYTES", "1000000")
    importlib.reload(walk)
    assert (walk.MAX_FILES, walk.MAX_FILE_BYTES) == (20000, 1000000)


def test_walk_skips_unsupported_and_oversized_files(tmp_path, monkeypatch):
    """Only source files walk in: a .md file is skipped (no language),
    and a file over the byte cap is skipped instead of crashing the run."""
    (tmp_path / "code.py").write_text("x = 1\n")
    (tmp_path / "notes.md").write_text("# notes\n")
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 100)
    assert walk.walk_repo(str(tmp_path)) == [
        ("big.py", str(big), "python"),
        ("code.py", str(tmp_path / "code.py"), "python"),
    ]
    monkeypatch.setattr(walk, "MAX_FILE_BYTES", 10)
    assert walk.walk_repo(str(tmp_path)) == [
        ("code.py", str(tmp_path / "code.py"), "python"),
    ]  # big.py (600 bytes) skipped; code.py (6 bytes) still walks in


def test_walk_raises_when_repo_exceeds_file_cap(tmp_path, monkeypatch):
    """Past MAX_FILES files, walk fails loudly instead of silently
    analyzing a partial repo."""
    for i in range(3):
        (tmp_path / f"f{i}.py").write_text("x = 1\n")
    monkeypatch.setattr(walk, "MAX_FILES", 2)
    with pytest.raises(walk.WalkError, match="file analysis cap"):
        walk.walk_repo(str(tmp_path))
