"""Which files an auto-PR may delete.

The eligibility rule is the product's trust contract: only ghost FILES
with LOW deletion risk (confidence >= 0.85, whole file unreferenced)
make the cut. Symbols are never auto-deleted (a stray function can be
re-exported dynamically in ways static edges miss), and MED/HIGH risk
files stay in the file table for human review. A requested file list
must be an exact subset of the eligible set, so a client can never talk
the API into deleting a file the analysis did not clear.
"""

SAFE_KIND = "file"
SAFE_RISK = "LOW"
MAX_FILES_PER_PR = 8  # matches the dashboard PR preview page


class SelectionError(Exception):
    """A rejected file selection, with an API-facing code and message."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def eligible_files(report: dict) -> list:
    """Every ghost the auto-PR is allowed to delete, safest first."""
    ghosts = report.get("ghosts", [])
    safe = [
        g
        for g in ghosts
        if g.get("ghost_kind") == SAFE_KIND and g.get("risk") == SAFE_RISK
    ]
    # ponytail: ghosts arrive sorted by savings, not confidence; the PR
    # deletes the safest files first, so re-sort here. Under a few
    # hundred ghosts a sort is free.
    safe.sort(key=lambda g: -g.get("confidence", 0))
    return safe[:MAX_FILES_PER_PR]


def select_files(report: dict, requested: list | None) -> list:
    """Validate a client-requested file list against the eligible set.

    requested=None means "everything eligible". Raises SelectionError
    for anything else that is not an exact non-empty subset.
    """
    eligible = eligible_files(report)
    if not eligible:
        raise SelectionError(
            "no_safe_files",
            "this report has no low-risk ghost files, nothing to open a PR for",
        )
    by_path = {g["path"]: g for g in eligible}
    if requested is None:
        return eligible
    if not requested:
        raise SelectionError(
            "empty_selection", "select at least one file to delete"
        )
    if len(requested) > MAX_FILES_PER_PR:
        raise SelectionError(
            "too_many_files",
            f"at most {MAX_FILES_PER_PR} files per PR, split it into two",
        )
    if len(set(requested)) != len(requested):
        raise SelectionError(
            "duplicate_file_selection",
            "each file may appear only once in a selection",
        )
    unknown = [p for p in requested if p not in by_path]
    if unknown:
        raise SelectionError(
            "invalid_file_selection",
            "not cleared for auto-delete: " + ", ".join(unknown[:5]),
        )
    return [by_path[p] for p in requested]
