"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import ReportTabs from "@/components/ReportTabs";
import { SampleTag } from "@/components/ReportView";
import { int, riskLabel } from "@/lib/format";
import type { GraphNode, Report } from "@/lib/api";

const GraphCanvas = dynamic(() => import("@/components/GraphCanvas"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[620px] items-center justify-center border border-line bg-white text-sm text-ink-soft">
      Loading the graph canvas...
    </div>
  ),
});

export default function GraphView({
  report,
  base,
  sample = false,
}: {
  report: Report;
  base: string;
  sample?: boolean;
}) {
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const [ghostOnly, setGhostOnly] = useState(false);

  const incoming = useMemo(() => {
    const counts = new Map<string, number>();
    for (const e of report.graph.edges) {
      counts.set(e.target, (counts.get(e.target) ?? 0) + 1);
    }
    return counts;
  }, [report]);

  const ghostInfo = selected
    ? report.ghosts.find((g) => g.path === selected.path)
    : undefined;

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight">
        {report.repo}: dependency graph
        {sample && <SampleTag />}
      </h1>
      <div className="mt-4">
        <ReportTabs base={base} active="graph" />
      </div>
      <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-ink-soft">
        <input
          type="checkbox"
          checked={ghostOnly}
          onChange={(e) => setGhostOnly(e.target.checked)}
          className="h-4 w-4 accent-[#059669]"
        />
        Highlight ghost nodes only
      </label>
      <div className="mt-4 flex flex-col gap-6 lg:flex-row">
        <div className="min-w-0 flex-1 overflow-hidden rounded-lg border border-line bg-white">
          <GraphCanvas
            graph={report.graph}
            ghostOnly={ghostOnly}
            onSelect={setSelected}
          />
        </div>
        <aside className="w-full shrink-0 lg:w-80">
          {selected ? (
            <div className="rounded-lg border border-line bg-white p-6">
              <p className="break-all font-mono text-sm font-medium">
                {selected.path}
              </p>
              <dl className="mt-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <dt className="text-ink-soft">LOC</dt>
                  <dd className="font-mono tabular-nums">{int(selected.loc)}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-ink-soft">Incoming edges</dt>
                  <dd className="font-mono tabular-nums">
                    {incoming.get(selected.id) ?? 0}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-ink-soft">Status</dt>
                  <dd
                    className={
                      selected.ghost ? "font-medium text-moss-deep" : ""
                    }
                  >
                    {selected.ghost ? "Ghost" : "Healthy"}
                  </dd>
                </div>
                {ghostInfo && (
                  <div className="pt-2">
                    <dt className="text-ink-soft">Confidence</dt>
                    <dd className="mt-1">
                      {riskLabel(ghostInfo.risk)} risk: {ghostInfo.reasons[0]}
                    </dd>
                  </div>
                )}
              </dl>
              <Link
                href={`${base}/prs/1`}
                className="mt-6 inline-block rounded-md bg-moss px-4 py-2 text-sm font-medium text-white hover:bg-moss-deep"
              >
                Preview PR
              </Link>
            </div>
          ) : (
            <div className="rounded-lg border border-line bg-white p-6 text-sm text-ink-soft">
              Click a node to inspect it. Ghost nodes are emerald: zero
              incoming edges in the dependency graph.
            </div>
          )}
        </aside>
      </div>
      {report.graph.truncated && (
        <p className="mt-4 text-sm text-ink-soft">
          Showing the 500 largest nodes. The full graph is in the report JSON.
        </p>
      )}
    </div>
  );
}
