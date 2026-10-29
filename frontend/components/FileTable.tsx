"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { GhostEntry, Report } from "@/lib/api";
import { csvCell, int, riskLabel, usd } from "@/lib/format";

type SortKey = "path" | "loc" | "annual_saving_usd" | "risk";
type TypeFilter = "all" | "file" | "symbol";
type RiskFilter = "all" | "LOW" | "MED" | "HIGH";

const RISK_ORDER = { LOW: 0, MED: 1, HIGH: 2 };

function typeLabel(g: GhostEntry): string {
  if (g.ghost_kind === "file") return "File";
  const k = g.kind ?? "symbol";
  return k.charAt(0).toUpperCase() + k.slice(1);
}

function downloadCsv(report: Report) {
  const rows = [
    ["path", "type", "loc", "annual_saving_usd", "risk", "confidence"],
    ...report.ghosts.map((g) => [
      g.path,
      typeLabel(g),
      String(g.loc),
      String(g.annual_saving_usd),
      riskLabel(g.risk),
      String(g.confidence),
    ]),
  ];
  const csv = rows.map((r) => r.map(csvCell).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  // repo is "owner/repo": a slash in a download filename is not portable.
  a.download = `${report.repo.replace("/", "-")}-ghostcode.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function FileTable({
  report,
  base,
}: {
  report: Report;
  base: string;
}) {
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("all");
  const [riskFilter, setRiskFilter] = useState<RiskFilter>("all");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("annual_saving_usd");
  const [sortDir, setSortDir] = useState<1 | -1>(-1);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = report.ghosts.filter(
      (g) =>
        (typeFilter === "all" || g.ghost_kind === typeFilter) &&
        (riskFilter === "all" || g.risk === riskFilter) &&
        (!q || g.path.toLowerCase().includes(q)),
    );
    const val = (g: GhostEntry) =>
      sortKey === "risk" ? RISK_ORDER[g.risk] : g[sortKey];
    return [...filtered].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      if (va === vb) return a.path.localeCompare(b.path);
      return (va < vb ? -1 : 1) * sortDir;
    });
  }, [report, typeFilter, riskFilter, query, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setSortDir(key === "path" ? 1 : -1);
    }
  }

  const headers: { key: SortKey; label: string }[] = [
    { key: "path", label: "File" },
    { key: "loc", label: "LOC" },
    { key: "annual_saving_usd", label: "$ Saved/yr" },
    { key: "risk", label: "Risk" },
  ];

  return (
    <div>
      <div className="flex flex-wrap gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value as TypeFilter)}
          aria-label="Filter by type"
          className="rounded-md border border-line bg-white px-3 py-2 text-sm"
        >
          <option value="all">All types</option>
          <option value="file">Files</option>
          <option value="symbol">Functions</option>
        </select>
        <select
          value={riskFilter}
          onChange={(e) => setRiskFilter(e.target.value as RiskFilter)}
          aria-label="Filter by risk"
          className="rounded-md border border-line bg-white px-3 py-2 text-sm"
        >
          <option value="all">All risks</option>
          <option value="LOW">Low</option>
          <option value="MED">Medium</option>
          <option value="HIGH">High</option>
        </select>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by path"
          aria-label="Search by path"
          className="min-w-0 flex-1 rounded-md border border-line bg-white px-3 py-2 text-sm placeholder:text-ink-soft/60 focus:border-moss focus:outline-none"
        />
      </div>

      {rows.length === 0 ? (
        <div className="mt-6 rounded-lg border border-line bg-white p-8 text-center">
          <p className="font-medium">Nothing matches these filters.</p>
          <p className="mt-2 text-sm text-ink-soft">
            Loosen a filter, or celebrate: fewer ghosts is the goal.
          </p>
        </div>
      ) : (
        <div className="mt-6 overflow-x-auto rounded-lg border border-line bg-white">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-line text-ink-soft">
                {headers.map((h) => (
                  <th
                    key={h.key}
                    className="px-4 py-3 font-medium"
                    // the arrow glyph is aria-hidden, so without this a
                    // screen reader never learns the current sort state
                    aria-sort={
                      sortKey === h.key
                        ? sortDir === 1
                          ? "ascending"
                          : "descending"
                        : "none"
                    }
                  >
                    <button
                      onClick={() => toggleSort(h.key)}
                      className="hover:text-ink"
                    >
                      {h.label}
                      {sortKey === h.key && (
                        <span aria-hidden>{sortDir === 1 ? " ↑" : " ↓"}</span>
                      )}
                    </button>
                  </th>
                ))}
                <th className="px-4 py-3 font-medium">Type</th>
                <th className="px-4 py-3 font-medium">
                  <span className="sr-only">Action</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {rows.map((g) => (
                <tr key={`${g.ghost_kind}:${g.path}:${g.name ?? ""}`}>
                  <td className="max-w-md truncate px-4 py-3 font-mono text-[13px]">
                    {g.path}
                    {g.ghost_kind === "symbol" && g.name && (
                      <span className="text-ink-soft"> :: {g.name}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 tabular-nums">{int(g.loc)}</td>
                  <td className="px-4 py-3 font-mono tabular-nums">
                    {usd(g.annual_saving_usd)}
                  </td>
                  <td className="px-4 py-3">{riskLabel(g.risk)}</td>
                  <td className="px-4 py-3 text-ink-soft">{typeLabel(g)}</td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`${base}/prs/1`}
                      className="font-medium text-moss-deep underline"
                    >
                      Preview PR
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <button
        onClick={() => downloadCsv(report)}
        className="mt-4 text-sm font-medium text-moss-deep underline"
      >
        Export CSV
      </button>
    </div>
  );
}
