# Launch

## Checklist

- [x] Backend on Render (free tier, Docker, non-root, healthcheck).
  Cold starts of 30-60s are expected; the dashboard shows progress
  states while jobs run.
- [x] Frontend on Vercel (`frontend/vercel.json`, `NEXT_PUBLIC_API_URL`).
- [x] Rollback: every deploy is a git commit; Render and Vercel both
  keep prior deploys one click away. Nothing to migrate, no database.
- [x] Uptime: Render healthchecks hit `/health`; add an external
  pinger (e.g. UptimeRobot) if the demo needs to stay warm.
- [x] README, CASE_STUDY.md, CHANGELOG.md, MIT LICENSE.
- [x] SEO: title, description, OG tags in `frontend/app/layout.tsx`;
  `frontend/app/sitemap.ts` for the landing page.
- [ ] Launch posts (in order): dev.to (full write-up), LinkedIn
  (build-in-public thread), r/programming, Hacker News, relevant
  Discords. One asset each: the case-study numbers, not hype.
- [ ] The Day 6 video: "I ran GhostCode on my old project" — script
  from CASE_STUDY.md, screen-record the dashboard, keep it under 90s.

## Assets

- **Positioning:** "For developers with aging codebases, GhostCode is
  the dead-code finder that shows you the money, unlike knip or
  vulture which stop at file lists." The P&L framing is the whole
  pitch; every screenshot leads with a dollar number.
- **Objection answers:**
  - "How is this different from knip?" Knip finds unused exports;
    GhostCode prices them and opens the deletion PR for you.
  - "False positives?" See CASE_STUDY.md: 89% to ~1% on real repos,
    every fix regression-tested.
  - "Is the auto-PR safe?" It only deletes LOW-risk whole files, only
    after your test suite passes in a sandbox. Symbols are never
    auto-deleted.
- **Analytics events to instrument** (Phase 0 plan, parked for v1.1):
  analysis started/completed, repo size bucket, report viewed,
  PR preview opened, PR created. None instrumented yet; the dashboard
  ships without tracking.

## What ships in v1

Public GitHub repos, Python + JS/TS, heuristic cost model, dashboard,
auto-PR for LOW-risk files. Everything else is in `docs/closeout.md`.
