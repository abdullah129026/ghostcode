# Build close-out (2026-10-21)

## Assumptions log, revisited

- "Groq free tier suffices for the stretch LLM pricing pass."
  **Parked.** The heuristic cost model shipped; LLM pricing never made
  the cut. See v2 list.
- "Render free tier cold starts acceptable for analysis jobs."
  **Validated.** Dashboard shows progress states during the 30-60s
  cold start; acceptable for a free demo.
- "Target repos have runnable test suites for the auto-PR gate."
  **Validated in tests, unproven in the wild.** The sandbox runs
  pytest/npm when found and blocks the PR otherwise. First real-world
  auto-PR will confirm.
- "tree-sitter grammars cover real-world Python/JS/TS."
  **Validated.** Three real repos parsed cleanly, including TSX and
  type annotations.

## OUT list, parked for v2 (with rationale)

- **More languages.** Python + JS/TS done properly beats five
  languages done sloppily. Each new language needs its own
  entry-point and framework rules (the Day 7 list proves it).
- **Private-repo OAuth.** v1 has no accounts; OAuth adds auth,
  token storage, and abuse surface for zero portfolio value.
- **LLM pricing pass.** The heuristic is auditable and free; an LLM
  pass needs a key, costs money, and invites argued-with numbers.
- **Incremental analysis.** Needs report diffing and caching; v1
  reports are cheap enough to rebuild.
- **IDE plugins and team dashboards.** Distribution, not analysis.
- **Monorepo-aware analysis.** Nested import roots need workspace
  config; explicitly out of scope (see CASE_STUDY.md limitations).
- **Method-level auto-PR.** File-level only in v1; methods need type
  tracking to be safe (see CASE_STUDY.md limitations).

## What would change with more time

Type tracking for method calls on annotated receivers, React
lifecycle awareness, and the analytics events from the launch plan.
None of them block v1's promise: safe file-level deletes with real
numbers.
