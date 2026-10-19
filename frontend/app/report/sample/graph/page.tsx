import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import GraphView from "@/components/GraphView";
import { getSampleReport } from "@/lib/sample";

export default function SampleGraphPage() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <SiteHeader />
      <main className="mx-auto max-w-6xl px-6 py-10">
        <GraphView report={getSampleReport()} base="/report/sample" sample />
      </main>
      <SiteFooter />
    </div>
  );
}
