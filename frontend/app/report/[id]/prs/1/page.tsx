"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import PrPreview from "@/components/PrPreview";
import { useReport } from "@/hooks/useReport";
import { API_BASE } from "@/lib/api";
import { int, usd } from "@/lib/format";

type PrPhase =
  | { kind: "idle" }
  | { kind: "running"; prJobId: string }
  | { kind: "done"; prUrl: string; testSummary: string | null }
  | { kind: "failed"; code: string; message: string };

const ERROR_COPY: Record<string, string> = {
  no_test_suite:
    "No test suite found in the repo. GhostCode only opens the PR after a green sandbox test run, so add a pytest or npm test suite and re-run the analysis.",
  tests_failed:
    "The sandbox test run failed after the deletions, so no PR was opened. One of these files is probably load-bearing; check the failing tests.",
  clone_failed:
    "The repo could not be cloned. Check that the URL is right and the repo is public, then try again.",
  push_failed:
    "The branch could not be pushed. Your token needs write access to this repo (a classic PAT with the repo scope works).",
  pr_failed:
    "The branch was pushed but the pull request could not be opened. You can open it by hand from the pushed branch.",
};

async function postPr(jobId: string, token: string, files: string[]) {
  const resp = await fetch(`${API_BASE}/pr`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ job_id: jobId, github_token: token, files }),
  });
  const body = await resp.json();
  if (!resp.ok) throw new Error(body?.error?.message ?? "request failed");
  return body.pr_job_id as string;
}

async function getPrJob(prJobId: string) {
  const resp = await fetch(`${API_BASE}/pr-jobs/${prJobId}`);
  if (!resp.ok) throw new Error("poll failed");
  return resp.json();
}

export default function PrPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const base = `/report/${id}`;
  const { report, error } = useReport(id);

  const safeFiles = (report?.ghosts ?? [])
    .filter((g) => g.ghost_kind === "file" && g.risk === "LOW")
    .slice(0, 8);
  const totalLoc = safeFiles.reduce((n, g) => n + g.loc, 0);
  const totalSaving = safeFiles.reduce((n, g) => n + g.annual_saving_usd, 0);

  const [selected, setSelected] = useState<string[] | null>(null);
  const [token, setToken] = useState("");
  const [phase, setPhase] = useState<PrPhase>({ kind: "idle" });
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (selected === null && safeFiles.length > 0) {
      setSelected(safeFiles.map((f) => f.path));
    }
  }, [safeFiles.length]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(
    () => () => {
      if (timer.current) clearInterval(timer.current);
    },
    []
  );

  const poll = (prJobId: string) => {
    timer.current = setInterval(async () => {
      try {
        const job = await getPrJob(prJobId);
        if (job.status === "done") {
          if (timer.current) clearInterval(timer.current);
          setPhase({
            kind: "done",
            prUrl: job.pr_url,
            testSummary: job.test_summary ?? null,
          });
        } else if (job.status === "error") {
          if (timer.current) clearInterval(timer.current);
          setPhase({
            kind: "failed",
            code: job.error?.code ?? "pr_failed",
            message: job.error?.message ?? "the auto-PR run failed",
          });
        }
      } catch {
        if (timer.current) clearInterval(timer.current);
        setPhase({
          kind: "failed",
          code: "poll_failed",
          message: "lost contact with the backend, refresh to check again",
        });
      }
    }, 3000);
  };

  const submit = async () => {
    const files = selected ?? [];
    if (files.length === 0 || token.trim().length === 0) return;
    setPhase({ kind: "idle" });
    try {
      const prJobId = await postPr(id, token.trim(), files);
      setPhase({ kind: "running", prJobId });
      poll(prJobId);
    } catch (e) {
      setPhase({
        kind: "failed",
        code: "request_failed",
        message: e instanceof Error ? e.message : "request failed",
      });
    }
  };

  const toggle = (path: string) =>
    setSelected((prev) => {
      const cur = prev ?? [];
      return cur.includes(path)
        ? cur.filter((p) => p !== path)
        : [...cur, path];
    });

  const running = phase.kind === "running";
  const canSubmit =
    !running &&
    (selected ?? []).length > 0 &&
    token.trim().length > 0 &&
    phase.kind !== "done";

  const action = (
    <div className="mt-4">
      {phase.kind === "done" ? (
        <div>
          <p className="text-sm font-medium text-ink">
            Pull request opened{phase.testSummary ? `, ${phase.testSummary}` : ""}.
          </p>
          <a
            href={phase.prUrl}
            target="_blank"
            rel="noreferrer"
            className="mt-3 inline-block rounded-md bg-moss px-5 py-2.5 text-sm font-medium text-white hover:bg-moss-deep"
          >
            View the pull request
          </a>
        </div>
      ) : (
        <>
          <fieldset className="space-y-2">
            <legend className="mb-2 text-sm font-medium text-ink">
              Files to delete
            </legend>
            {safeFiles.map((f) => (
              <label
                key={f.path}
                className="flex cursor-pointer items-center gap-3 rounded-md border border-line px-3 py-2 text-sm hover:border-ink-soft"
              >
                <input
                  type="checkbox"
                  checked={(selected ?? []).includes(f.path)}
                  onChange={() => toggle(f.path)}
                  disabled={running}
                  className="h-4 w-4 accent-[#059669]"
                />
                <span className="font-mono">{f.path}</span>
                <span className="ml-auto font-mono text-xs tabular-nums text-ink-soft">
                  -{int(f.loc)} lines
                </span>
              </label>
            ))}
          </fieldset>

          <div className="mt-4">
            <label
              htmlFor="gh-token"
              className="mb-2 block text-sm font-medium text-ink"
            >
              GitHub token
            </label>
            <input
              id="gh-token"
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="ghp_..."
              autoComplete="off"
              disabled={running}
              className="w-full rounded-md border border-line bg-paper px-3 py-2 font-mono text-sm focus:border-ink-soft focus:outline-none"
            />
            <p className="mt-2 text-xs text-ink-soft">
              A personal access token with repo scope, for this repo only.
              It is sent over HTTPS, used once to open the PR, and never
              stored.
            </p>
          </div>

          <button
            onClick={submit}
            disabled={!canSubmit}
            className="mt-4 rounded-md bg-moss px-5 py-2.5 text-sm font-medium text-white hover:bg-moss-deep disabled:cursor-not-allowed disabled:opacity-40"
          >
            {running ? "Working..." : "Open pull request"}
          </button>

          {running && (
            <p className="mt-3 text-sm text-ink-soft">
              Cloning the repo, deleting the files, and running the test
              suite in a sandbox. This takes a few minutes; the PR only
              opens if the tests pass.
            </p>
          )}
          {phase.kind === "failed" && (
            <div className="mt-3 rounded-md border border-clay/40 bg-clay/5 px-3 py-2.5">
              <p className="text-sm font-medium text-ink">
                {ERROR_COPY[phase.code] ?? phase.message}
              </p>
              {ERROR_COPY[phase.code] && (
                <p className="mt-1 font-mono text-xs text-ink-soft">
                  {phase.code}: {phase.message}
                </p>
              )}
            </div>
          )}
          <p className="mt-3 text-sm text-ink-soft">
            Deletions ship as pull requests, never direct pushes. Nothing
            is merged without your review.
          </p>
        </>
      )}
    </div>
  );

  return (
    <div className="min-h-screen bg-paper text-ink">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-10">
        {error ? (
          <div className="py-16 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">
              This report did not make it
            </h1>
            <p className="mx-auto mt-3 max-w-md text-sm text-ink-soft">
              {error}
            </p>
            <button
              onClick={() => router.push("/")}
              className="mt-6 rounded-md bg-moss px-5 py-2.5 text-sm font-medium text-white hover:bg-moss-deep"
            >
              Analyze another repo
            </button>
          </div>
        ) : !report ? (
          <p className="py-16 text-center text-sm text-ink-soft">
            Loading the report...
          </p>
        ) : safeFiles.length === 0 ? (
          <div className="py-16 text-center">
            <h1 className="text-2xl font-semibold tracking-tight">
              Nothing safe to delete yet
            </h1>
            <p className="mx-auto mt-3 max-w-md text-sm text-ink-soft">
              No low-risk ghost files in this report, so there is no PR to
              preview. Medium and high-risk findings stay in the file table
              for human review.
            </p>
          </div>
        ) : (
          <PrPreview
            title={`Safe-delete PR preview: ${report.repo}`}
            summary={`${safeFiles.length} files changed, ${int(totalLoc)} deletions, 0 additions. Est. savings ${usd(totalSaving)}/yr.`}
            files={safeFiles.map((g) => ({ path: g.path, loc: g.loc }))}
            sandboxLine="GhostCode branches the repo, deletes the selected files, and runs the repo's test suite in a sandbox. The pull request only opens on a green run."
            backHref={base}
            action={action}
          />
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
