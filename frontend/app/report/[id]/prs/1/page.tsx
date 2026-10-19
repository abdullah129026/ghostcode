"use client";

import { useParams, useRouter } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import PrPreview from "@/components/PrPreview";
import { useReport } from "@/hooks/useReport";
import { int, usd } from "@/lib/format";

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
            sandboxLine="Sandbox test runs arrive with Day 6 auto-PR. This preview is design-only: nothing here is wired to GitHub yet."
            backHref={base}
          />
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
