"""Auto-PR: turn a report's safe deletes into a real pull request.

Pipeline: select eligible files from the report -> clone the repo ->
branch -> delete -> commit -> sandbox test run -> push -> open the PR.
The PR only opens when the sandbox run is green. The GitHub token is
supplied per request, used in-memory only, and never logged.
"""
