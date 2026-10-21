# GhostCode Dogfood Case Study

Ship day, October 21. Before calling GhostCode done, I ran it on three
real repos: GhostCode itself, PRISM, and Spec2Run. All three are mine,
all three are actively maintained, and I know exactly what's dead in
them (almost nothing). That's what made the first run so useful.

## The embarrassing first run

The first analysis flagged **89% of GhostCode's own code as dead**,
including the FastAPI app entry point, the import resolver, and the
dead-code scorer itself. PRISM came back at 92% dead, Spec2Run at 72%.
The headline burn numbers ($5,981/year for GhostCode, $6,303 for PRISM)
were fiction.

A dead-code tool that flags live code is worse than no tool. So instead
of shipping, I spent the day hunting every false positive and fixing the
systematic ones. Thirteen classes, all verified with regression tests:

1. **Python src-layouts.** Repos with a `backend/` or `src/` directory
   keep absolute imports working via `sys.path`, but the resolver only
   tried the repo root. Every module looked unimported.
2. **`from app.routers import analyze`.** This imports the submodule
   *file*, not just the package. The file edge was missing, so every
   FastAPI router looked dead.
3. **Submodule attribute calls.** `from . import schema` then
   `schema.def_record()` resolved through the package `__init__`
   instead of the submodule file.
4. **Next.js framework entries.** Pages, layouts, and route handlers
   are never imported by name; the framework loads them by convention.
5. **Tooling configs and type declarations.** `next.config.mjs`,
   `tailwind.config.ts`, and `*.d.ts` files are consumed by tooling,
   not imports.
6. **`@/` path aliases.** The entire frontend imports via `@/lib/...`,
   which the resolver treated as an external package.
7. **Decorated functions.** FastAPI route handlers are registered by
   `@app.get`, never called by name.
8. **Default exports of entry files.** Next.js renders a page's default
   export; nothing imports it.
9. **Constructors and `d.ts` symbols.** Invoked by `new`, erased at
   compile time.
10. **Dynamic imports.** `next/dynamic(() => import("./Canvas"))`
    renders the default export.
11. **JSX references.** `<Progress />` and `onClick={onSelect}` are real
    references, including nested expressions.
12. **Call arguments.** `Depends(_limit)`, `Thread(target=_run)`,
    `addEventListener("keydown", onKey)` pass functions by reference.
13. **Returns and annotations.** `return _inner` and
    `def f(req: CodeRequest)` are uses, not dead code.

## After the fixes

| Repo | Files | Ghost LOC | Burn/year | File ghosts |
|------|-------|-----------|-----------|-------------|
| GhostCode | 82 | 1.0% | $53.53 | 0 in product code |
| PRISM | 50 | 0.8% | $30.82 | 0 |
| Spec2Run | 46 | 0.0% | $0.00 | 0 |

GhostCode's 4 remaining file ghosts are all in `backend/ingest/fixtures/`,
the tool's own test data with intentionally-dead code. Spec2Run came
back completely clean, which is the right answer for a one-week-old
codebase with no dead code.

## Real findings in PRISM

Two verified true positives, both confirmed by hand:

- **`warmIntentCache`** (`frontend/lib/api.ts`, 10 LOC, ~$5.75/year):
  exported, never imported anywhere in the frontend.
- **`list_intents`** (`backend/app/services/jobs.py`, 4 LOC, ~$3.20/year):
  method on the jobs service, never called.

Small numbers, but that's the point: these are clean repos, and the
tool now says so instead of inventing thousands of dollars in fake
savings.

## Known limitations (v1)

Documented, not hidden:

- Methods called on receivers the analyzer can't track
  (`store.create()` where `store` is annotated, `app.state.x.allow()`).
  Fixing this needs type tracking.
- React lifecycle methods (`render`, `getDerivedStateFromError`) and
  framework config methods (`rewrites()` in `next.config.js`).
- Test fixtures with their own import roots nested inside the repo.
  Monorepo-aware analysis is explicitly out of scope for v1.

## The takeaway

The first run was the most valuable test GhostCode ever had. A tool
that can't survive its own codebase can't be trusted on anyone else's.
The thirteen fixes above are all covered by regression tests, and the
fixture suite (which pins the known ghost sets) stayed green through
every one of them.
