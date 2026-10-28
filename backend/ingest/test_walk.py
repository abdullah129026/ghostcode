"""Walk env caps: garbage GHOSTCODE_MAX_* must fall back to defaults.

Same gap as the sandbox caps: commit 3cc9d09 made the api package
tolerate mistyped numeric env vars at import, but ingest/walk.py still
crashed the whole service at boot on a bad value. Reloading re-reads
the env; the last block restores the pristine defaults so later tests
see the same constants a fresh import would.
"""

import importlib

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
