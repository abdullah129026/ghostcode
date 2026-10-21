# Compliance

## Dependency licenses (audited 2026-10-21)

All MIT/BSD-3 except PyGithub (LGPL-2.1), which is used unmodified as
a library by the backend service. No GPL/AGPL anywhere in the tree.
No copyleft distribution occurs (the backend runs server-side; the
dashboard ships no LGPL code to browsers).

Backend (`requirements.txt`, pinned):

| Package | License |
|---------|---------|
| networkx 3.7 | BSD-3-Clause |
| tree-sitter 0.26.0, tree-sitter-python/javascript/typescript | MIT |
| fastapi 0.143.3 | MIT |
| starlette 1.8.0 | BSD-3-Clause |
| uvicorn 0.54.0 | BSD-3-Clause |
| httpx2 2.13.1 | MIT |
| PyGithub 2.10.0 | LGPL-2.1 (unmodified library use) |
| pytest 9.1.1 | MIT (test only) |

Frontend (`package.json`): next, react, react-dom,
react-force-graph-2d, typescript, tailwindcss, postcss, autoprefixer
are all MIT. `@types/*` are MIT.

GhostCode itself is MIT (see `LICENSE`).

## Cloned-code policy

- Repos are cloned shallow (`--depth 1`) into a tempdir for analysis
  only, and only from `https://github.com/` URLs (allowlisted,
  validated, no credentials in URLs).
- The clone is deleted when the job settles, success or failure. No
  cloned code is persisted, logged, or used for training.
- Size and time caps on clones; clean errors, never a hung worker.
- Never log cloned code contents or repo URLs containing tokens.
