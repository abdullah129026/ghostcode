"""Confidence scoring for ghost files and symbols.

A ghost has zero incoming edges. That answers "is it dead", not "is it
safe to delete". The score here is deletion confidence (0.0 to 1.0) plus
the risk level and the reasons the dashboard shows next to each row.
Every score carries its reasons because a risk flag with no reason is
not actionable (prompt 0.2, baked in now).

Confidence is heuristic by design: static analysis cannot see dynamic
usage, so the scorer looks for the usual hiding places (stringly-typed
references, wildcard imports, getattr/eval) and dings confidence when it
finds them. Conservative on purpose: a false "safe to delete" costs more
trust than a missed deletion.
"""

import re

_BASE_CONFIDENCE = 0.90
_FILE_BONUS = 0.05  # whole unused files delete cleaner than stray symbols
_STRING_REF_PENALTY = 0.25
_WILDCARD_PENALTY = 0.15
_DYNAMIC_PENALTY = 0.15

_MAX_CONFIDENCE = 0.99  # static analysis never proves anything
_MIN_CONFIDENCE = 0.05


def _quoted_name_pattern(name):
    # Matches 'name' or "name" as a substring of a string literal, the
    # classic config/plugin/registry lookup that static edges miss.
    return re.compile(
        rb"['\"`][^'\"`\n]{0,80}\b" + re.escape(name.encode()) + rb"\b[^'\"`\n]{0,80}['\"`]"
    )


_WILDCARD_RE = re.compile(rb"from\s+[\w.]+\s+import\s+\*|import\s+\*\s+as\s+\w+")
_DYNAMIC_RE = re.compile(rb"__getattr__|\b(getattr|eval|exec)\s*\(")


def _repo_flags(sources):
    """Repo-wide dynamic-usage evidence, computed once per run."""
    blob = b"\n".join(sources.values())
    return {
        "wildcard": bool(_WILDCARD_RE.search(blob)),
        "dynamic": bool(_DYNAMIC_RE.search(blob)),
        "blob": blob,
    }


def _score_one(ghost, kind, flags):
    reasons = [ghost["reason"]]
    confidence = _BASE_CONFIDENCE

    if kind == "file":
        confidence += _FILE_BONUS
        reasons.append("entire file is unreferenced, deletes as one unit")
    else:
        name = ghost["name"] or ""
        if name and _quoted_name_pattern(name).search(flags["blob"]):
            confidence -= _STRING_REF_PENALTY
            reasons.append(
                f"name '{name}' appears in a string literal: "
                "it may be looked up dynamically"
            )

    if flags["wildcard"]:
        confidence -= _WILDCARD_PENALTY
        reasons.append("repo uses wildcard imports: some usages may be invisible")
    if flags["dynamic"]:
        confidence -= _DYNAMIC_PENALTY
        reasons.append(
            "repo uses getattr/eval/exec or __getattr__: "
            "dynamic dispatch may hide callers"
        )

    confidence = max(_MIN_CONFIDENCE, min(_MAX_CONFIDENCE, confidence))
    confidence = round(confidence, 2)
    if confidence >= 0.85:
        risk = "LOW"
    elif confidence >= 0.60:
        risk = "MED"
    else:
        risk = "HIGH"
    return {
        **ghost,
        "ghost_kind": kind,
        "confidence": confidence,
        "risk": risk,
        "reasons": reasons,
    }


def score_ghosts(ghost_report, records, sources):
    """Attach confidence, risk, and reasons to every ghost.

    ghost_report is detect_ghosts() output. Returns a list sorted by
    confidence descending (safest deletes first), files before symbols
    on ties.
    """
    flags = _repo_flags(sources)
    scored = [
        _score_one(entry, "file", flags) for entry in ghost_report["files"]
    ] + [
        _score_one(entry, "symbol", flags) for entry in ghost_report["symbols"]
    ]
    scored.sort(key=lambda g: (g["ghost_kind"] != "file", -g["confidence"]))
    return scored
