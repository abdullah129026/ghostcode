"use client";

import { useParams, useRouter } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import GraphView from "@/components/GraphView";
import { Button } from "@/components/ui/button";
import { useReport } from "@/hooks/useReport";

export default function GraphPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const base = `/report/${id}`;
  const { report, error } = useReport(id);

  return (
    <div className="min-h-screen text-ink">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 py-10">
        {error ? (
          <div className="py-16 text-center" role="alert">
            <h1 className="text-2xl font-semibold tracking-tight">
              This report did not make it
            </h1>
            <p className="mx-auto mt-3 max-w-md text-sm text-ink-soft">
              {error}
            </p>
            <Button onClick={() => router.push("/")} className="mt-6">
              Analyze another repo
            </Button>
          </div>
        ) : !report ? (
          <p className="py-16 text-center text-sm text-ink-soft">
            Loading the report...
          </p>
        ) : (
          <GraphView report={report} base={base} />
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
