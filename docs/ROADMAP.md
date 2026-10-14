# GhostCode — 7-Day Roadmap

**Pitch:** Turns dead code into a P&L statement. Upload any GitHub repo, get a dependency
graph plus: "You have 18% dead code. It's costing you ~$4,200/year in CI + maintenance.
Here are 3 safe-to-delete PRs."

**Window:** 2026-10-15 → 2026-10-21 (1-week pace).
**Stack:** Python, FastAPI, tree-sitter, NetworkX, GitPython (backend) / Next.js 14 +
Tailwind (frontend) / Docker / $0 (Render + Vercel).
**Languages:** Python + JavaScript/TypeScript only. Done perfectly beats 20 languages done badly.

## Day 1 — Wed Oct 15: Scaffold + Ingestion
- [ ] Repo layout: `backend/` (FastAPI), `frontend/` (Next.js), `Dockerfile`s, `.github/workflows/ci.yml`
- [ ] tree-sitter parsing for Python + JS/TS: extract imports, exports, function/class defs
- [ ] CLI: `python -m ghostcode --repo <github-url> --format json` prints the raw graph JSON
- [ ] Pinned deps, CI green

## Day 2 — Thu Oct 16: Graph core (the IP)
- [ ] NetworkX graph: nodes = files/functions/classes, edges = imports/calls/inherits
- [ ] Entry-point analysis (`main.py`, `index.js`, `__main__`, package.json main)
- [ ] Ghost node detection: 0 incoming edges after entry-point pruning
- [ ] Unit tests on 3 fixture repos (small hand-made ones)

## Day 3 — Fri Oct 17: Analysis engines
- [ ] Dead-code scorer (unreachable nodes, ranked by LOC)
- [ ] Duplication: AST subtree hash for Python, jscpd or token-hash for JS
- [ ] Circular imports (A→B→A) and huge files (>500 LOC) flagged as debt
- [ ] Cost engine (heuristic): `LOC × $0.50 × complexity factor` → $/year burn per node
- [ ] Stretch: LLM pricing pass via Groq (maintenance cost + refactor risk LOW/MED/HIGH)

## Day 4 — Sat Oct 18: API backend
- [ ] FastAPI: `POST /analyze` (GitHub URL or zip upload) → job id, `GET /report/{id}` → full JSON
- [ ] Background analysis (no request-timeout traps), input validation + bounds on repo size
- [ ] Dockerfile, `render.yaml`, deploy backend to Render, health check green

## Day 5 — Sun Oct 19: Dashboard
- [ ] Next.js: hero stats ("Ghost LOC: 4,120 | Est. annual burn: $2,840 | Safe PRs: 3")
- [ ] Graph view (react-force-graph), file table: File | Type | LOC | $ Saved | Risk | Action
- [ ] Follows docs/DESIGN-BRIEF.md; Inter; deployed to Vercel

## Day 6 — Mon Oct 20: Auto-PR (the viral moment)
- [ ] PyGithub: create branch `ghostcode/remove-<name>`, delete ghost files, commit
- [ ] Run existing tests (pytest / npm test) in sandbox; only open PR if green
- [ ] PR body: what was removed, LOC deleted, est. $ saved, test evidence

## Day 7 — Tue Oct 21: Ship it
- [ ] Dogfood: run on own portfolio repo, before/after numbers
- [ ] `CASE_STUDY.md`: 2 repos tested with real numbers
- [ ] README with system diagram (4 layers), demo instructions, resume-ready bullets
- [ ] LinkedIn-ready screenshot/gif of the dashboard

## Explicitly out of scope (future work)
- LLM cost pricing if heuristic ships first and time runs out (Day 3 stretch)
- More languages, private-repo OAuth, incremental analysis caching
