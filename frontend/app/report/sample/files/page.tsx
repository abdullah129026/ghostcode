import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import ReportTabs from "@/components/ReportTabs";
import FileTable from "@/components/FileTable";
import { SampleTag } from "@/components/ReportView";
import { getSampleReport } from "@/lib/sample";

export default function SampleFilesPage() {
  const report = getSampleReport();
  return (
    <div className="min-h-screen bg-paper text-ink">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <h1 className="text-xl font-semibold tracking-tight">
          {report.repo}: files
          <SampleTag />
        </h1>
        <div className="mt-4">
          <ReportTabs base="/report/sample" active="files" />
        </div>
        <div className="mt-6">
          <FileTable report={report} base="/report/sample" />
        </div>
        <p className="mt-6 text-sm text-ink-soft">
          <Link href="/report/sample" className="underline hover:text-ink">
            Back to the report
          </Link>
        </p>
      </main>
      <SiteFooter />
    </div>
  );
}
