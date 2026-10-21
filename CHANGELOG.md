# Changelog

## v1.0.0 — 2026-10-21

Seven-day build, shipped. Turns dead code into a P&L statement:
tree-sitter ingestion for Python and JS/TS, NetworkX dependency graph,
dead-code scorer with LOW/MED/HIGH risk, debt engine, heuristic cost
model, FastAPI backend, Next.js dashboard, and sandboxed auto-PRs.

- Day 7 dogfood found and fixed 13 false-positive classes (src-layouts,
  submodule imports, `@/` aliases, decorators, JSX, call args, and
  more); see `CASE_STUDY.md`.
- 137 backend tests green, frontend typechecks and builds clean.
