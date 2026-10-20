# ADR 0001: Auto-PR sandbox and token handling (Day 6)

Date: 2026-10-20. Status: accepted.

## Context

The auto-PR feature clones a repo, deletes files, and runs the repo's
own test suite before opening a pull request. Running untrusted test
code is the most dangerous thing this backend does. The brief demands
sandboxed test runs, and the budget is $0: the backend runs on Render's
free tier in a plain container, no Docker socket, no privileged
namespaces.

## Decision

Defense in depth with plain OS primitives (`backend/autopr/sandbox.py`):

1. Scrubbed environment, built from scratch (allowlist, not denylist).
   No secrets, no tokens, no GHOSTCODE_* variables survive.
2. `setrlimit` in a preexec_fn: CPU time, address space (2 GB), max
   file size (512 MB), process count (256). Fail closed if limits
   cannot be applied.
3. argv only, no shell. cwd pinned to the disposable clone.
   Wall-clock timeout per command (default 600 s).
4. Dependencies install inside the same sandbox. A failed install
   fails the gate instead of being skipped.
5. Raw test output never reaches the API. The job record keeps a
   tail server-side; the API reports a one-line verdict (counts only),
   because assertion diffs can contain source lines.

The gate rules, in order: no detectable test suite means no PR
(`no_test_suite`); a failing suite means no PR (`tests_failed`); only
a green run pushes the branch and opens the PR.

The GitHub token is supplied per request in the POST /pr body
(Pydantic SecretStr). It lives only in the worker thread's call stack,
is passed to `git push` as a one-shot URL argument (never written to
the repo config), and every error path redacts it before it can reach
a log line or an API response. It is never persisted.

Eligibility is the trust contract (`backend/autopr/select.py`): only
ghost FILES with LOW deletion risk (confidence >= 0.85) are deletable,
at most 8 per PR, and a client-supplied file list must be an exact
subset of the eligible set. Symbols and MED/HIGH risk files stay human.

## Consequences

- The sandbox does NOT isolate the network (no netns without
  privileges). Dependency installs and test runs can reach the
  internet. This is the known residual risk; the upgrade path is a
  real container boundary (Docker-in-Docker or gVisor) when the
  project outgrows the free tier.
- JS repos need node/npm in the image to run their suites; the current
  backend image has neither, so npm suites report `runner_unavailable`
  instead of silently passing. Adding node to the image is a
  follow-up, not a Day 6 scope change.
- PRs go to the user's own repo with their own token. Fork-based PRs
  (for repos the user cannot push to) are explicitly deferred to v2.

## Alternatives considered

- Docker-in-Docker on Render free: not available, no socket to mount.
- Skipping the test gate when no suite is found: rejected. The
  brief's hard rule is "the auto-PR never opens without a green
  sandbox test run", and a silent pass would be the exact false
  confidence this product exists to kill.
