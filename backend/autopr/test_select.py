import pytest

from autopr.select import (
    MAX_FILES_PER_PR,
    SelectionError,
    eligible_files,
    select_files,
)


def _ghost(path, kind="file", risk="LOW", confidence=0.95):
    return {
        "path": path,
        "ghost_kind": kind,
        "risk": risk,
        "confidence": confidence,
        "loc": 10,
    }


def _report(ghosts):
    return {"schema": 2, "ghosts": ghosts}


def test_eligible_keeps_only_low_risk_files():
    ghosts = [
        _ghost("a.py", risk="LOW"),
        _ghost("b.py", risk="MED"),
        _ghost("c.py", risk="HIGH"),
        _ghost("d.py", kind="symbol", risk="LOW"),
    ]
    assert [g["path"] for g in eligible_files(_report(ghosts))] == ["a.py"]


def test_eligible_sorts_safest_first_and_caps():
    ghosts = [
        _ghost(f"f{i}.py", confidence=0.86 + i * 0.001)
        for i in range(MAX_FILES_PER_PR + 3)
    ]
    got = eligible_files(_report(ghosts))
    assert len(got) == MAX_FILES_PER_PR
    confs = [g["confidence"] for g in got]
    assert confs == sorted(confs, reverse=True)


def test_select_none_means_all_eligible():
    ghosts = [_ghost("a.py"), _ghost("b.py", risk="MED")]
    assert [g["path"] for g in select_files(_report(ghosts), None)] == ["a.py"]


def test_select_rejects_unknown_and_non_safe_paths():
    ghosts = [_ghost("a.py"), _ghost("b.py", risk="MED")]
    with pytest.raises(SelectionError) as exc:
        select_files(_report(ghosts), ["a.py", "b.py"])
    assert exc.value.code == "invalid_file_selection"
    with pytest.raises(SelectionError) as exc:
        select_files(_report(ghosts), ["../escape.py"])
    assert exc.value.code == "invalid_file_selection"


def test_select_rejects_empty_and_missing():
    ghosts = [_ghost("a.py")]
    with pytest.raises(SelectionError) as exc:
        select_files(_report(ghosts), [])
    assert exc.value.code == "empty_selection"
    with pytest.raises(SelectionError) as exc:
        select_files(_report([_ghost("a.py", risk="HIGH")]), None)
    assert exc.value.code == "no_safe_files"
