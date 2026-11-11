"""Tests for the shared engine helpers in engines/__init__.py."""
def test_read_sources_skips_unreadable_file(tmp_path):
    """A record pointing at a file that no longer exists is skipped,
    not fatal: engines degrade, they don't crash the run."""
    from engines import read_sources

    records = [
        {"path": "live.py"},
        {"path": "gone.py"},
    ]
    (tmp_path / "live.py").write_text("def run():\n    pass\n")
    sources = read_sources(str(tmp_path), records)
    assert set(sources) == {"live.py"}
