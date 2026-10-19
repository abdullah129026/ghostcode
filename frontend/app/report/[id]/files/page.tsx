"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import ReportTabs from "@/components/ReportTabs";
import FileTable from "@/components/FileTable";
import { useReport } from "@/hooks/useReport";

export default function FilesPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const base = `/report/${id}`;
  const { report, error } = useReport(id);

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
        ) : (
          <div>
            <h1 className="text-xl font-semibold tracking-tight">
              {report.repo}: files
            </h1>
            <div className="mt-4">
              <ReportTabs base={base} active="files" />
            </div>
            <div className="mt-6">
              <FileTable report={report} base={base} />
            </div>
            <p className="mt-6 text-sm text-ink-soft">
              <Link href={base} className="underline hover:text-ink">
                Back to the report
              </Link>
            </p>
          </div>
        )}
      </main>
      <SiteFooter />
    </div>
  );
}
