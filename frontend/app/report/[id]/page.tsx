"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import ReportView from "@/components/ReportView";
import { useReport } from "@/hooks/useReport";

const STAGES = [
  "Cloning the repository",
  "Parsing files with tree-sitter",
  "Building the dependency graph",
  "Scoring ghost code",
  "Pricing the burn",
];

function Progress({ repo }: { repo: string }) {
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setElapsed((e) => e + 1), 1000);
    return () => clearInterval(t);
  }, []);
  const stage = Math.min(STAGES.length - 1, Math.floor(elapsed / 12));
  return (
    <div className="py-16">
      <p className="text-sm font-medium uppercase tracking-widest text-ink-soft">
        Analyzing
      </p>
      <h1 className="mt-2 font-mono text-2xl font-semibold tracking-tight">
        {repo}
      </h1>
      <ol className="mt-8 max-w-md space-y-3">
        {STAGES.map((s, i) => (
          <li
            key={s}
            className={`flex items-center gap-3 text-sm ${
              i < stage
                ? "text-ink-soft"
                : i === stage
                  ? "font-medium text-ink"
                  : "text-ink-soft/50"
            }`}
          >
            <span
              aria-hidden
              className={`inline-block h-2 w-2 rounded-full ${
                i < stage
                  ? "bg-moss"
                  : i === stage
                    ? "animate-pulse bg-moss"
                    : "bg-line"
              }`}
            />
            {s}
            {i < stage && <span className="text-moss">done</span>}
          </li>
        ))}
      </ol>
      <p className="mt-8 text-sm tabular-nums text-ink-soft">
        {elapsed}s elapsed. Large repos can take a few minutes; the page
        updates on its own.
      </p>
    </div>
  );
}

export default function ReportPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const { job, report, error, rerun, rerunning } = useReport(id);

  async function onRerun() {
    const nextId = await rerun();
    if (nextId) router.push(`/report/${nextId}`);
  }

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
        ) : report ? (
          <ReportView
            report={report}
            base={`/report/${id}`}
            onRerun={rerunning ? undefined : onRerun}
          />
        ) : (
          <Progress repo={job?.repo ?? id} />
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
