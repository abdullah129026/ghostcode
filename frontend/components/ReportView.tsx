import Link from "next/link";
import type { Report } from "@/lib/api";
import { int, pct, timeAgo, usd } from "@/lib/format";
import Stat from "@/components/Stat";
import ReportTabs from "@/components/ReportTabs";

export function SampleTag() {
  return (
    <span className="ml-3 inline-block rounded border border-amber px-2 py-0.5 align-middle text-xs font-medium uppercase tracking-wider text-amber">
      Sample report
    </span>
  );
}

export default function ReportView({
  report,
  base,
  sample = false,
  onRerun,
}: {
  report: Report;
  base: string;
  sample?: boolean;
  onRerun?: () => void;
}) {
  const s = report.summary;
  const safeDeletes = report.ghosts.filter((g) => g.risk === "LOW").length;
  const topFiles = report.ghosts
    .filter((g) => g.ghost_kind === "file")
    .slice(0, 5);

  return (
    <div>
      <p className="text-sm text-ink-soft">
        <Link href="/" className="hover:text-ink">
          Repositories
        </Link>{" "}
        / {report.repo} / Report
      </p>
      <div className="mt-2 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">
            {report.repo}
            {sample && <SampleTag />}
          </h1>
          <p className="mt-1 text-sm text-ink-soft">
            {int(s.files)} files, {int(s.total_loc)} LOC, analyzed{" "}
            {sample ? "2 hours ago" : timeAgo(report.generated_at)}
          </p>
        </div>
        {onRerun && (
          <button
            onClick={onRerun}
            className="rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss-deep"
          >
            Re-run analysis
          </button>
        )}
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 sm:grid-cols-3">
        <Stat label="Ghost LOC" value={s.ghost_loc} />
        <Stat label="Est. annual burn" value={usd(s.annual_burn_usd)} />
        <Stat label="Safe deletes (low risk)" value={safeDeletes} />
      </div>

      <p className="mt-6 max-w-3xl text-lg leading-relaxed">
        {pct(s.ghost_loc, s.total_loc)} of this codebase is never called.
        Deleting it saves about {usd(s.annual_burn_usd)} a year in CI and
        maintenance.
      </p>

      <div className="mt-8">
        <ReportTabs base={base} active="report" />
      </div>

      <h2 className="mt-10 text-xl font-semibold tracking-tight">
        Where it hurts
      </h2>
      {topFiles.length === 0 ? (
        <div className="mt-4 rounded-lg border border-line bg-white p-8 text-center">
          <p className="font-medium">No ghost files found. Ship it.</p>
          <p className="mt-2 text-sm text-ink-soft">
            Every file in this repo has at least one incoming edge. This is
            the good kind of boring.
          </p>
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-line border-y border-line">
          {topFiles.map((g) => (
            <li
              key={g.path}
              className="flex flex-wrap items-center justify-between gap-3 py-4"
            >
              <div>
                <p className="font-mono text-sm">{g.path}</p>
                <p className="mt-1 text-sm tabular-nums text-ink-soft">
                  {int(g.loc)} ghost LOC, {usd(g.annual_saving_usd)}/yr
                </p>
              </div>
              <div className="flex gap-4 text-sm font-medium">
                <Link
                  href={`${base}/graph`}
                  className="text-moss-deep underline"
                >
                  View in graph
                </Link>
                <Link
                  href={`${base}/prs/1`}
                  className="text-moss-deep underline"
                >
                  Preview PR
                </Link>
              </div>
            </li>
          ))}
        </ul>
      )}

      <p className="mt-10 border-t border-line pt-6 text-sm text-ink-soft">
        Ghost code means zero incoming edges in the dependency graph, weighted
        by the confidence scorer. The cost model is LOC x $0.50 x complexity.
      </p>
    </div>
  );
}
