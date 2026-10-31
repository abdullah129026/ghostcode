import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import PrPreview from "@/components/PrPreview";
import { getSampleReport } from "@/lib/sample";

// Sample PR copy from the design doc (labeled sample). Live reports render
// this layout from real auto-PR data; the sample keeps a disabled action
// because it has no repo to open a pull request against.
export default function SamplePrPage() {
  const report = getSampleReport();
  return (
    <div className="min-h-screen bg-paper text-ink">
      <SiteHeader />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <PrPreview
          title="PR 1 of 3: Remove unused billing helpers"
          summary="14 files changed, 2,310 deletions, 0 additions. Est. savings $780/yr."
          files={report.ghosts
            .filter((g) => g.ghost_kind === "file")
            .map((g) => ({ path: g.path, loc: g.loc }))}
          sandboxLine="Sandbox tests: 142 passed, 0 failed (pytest, 38s). The repo's own test suite approved every deletion."
          sample
          backHref="/report/sample"
        />
      </main>
      <SiteFooter />
    </div>
  );
}
