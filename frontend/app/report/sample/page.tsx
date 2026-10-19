import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import ReportView from "@/components/ReportView";
import { getSampleReport } from "@/lib/sample";

export default function SampleReportPage() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <ReportView report={getSampleReport()} base="/report/sample" sample />
      </main>
      <SiteFooter />
    </div>
  );
}
