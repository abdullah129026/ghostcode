import Link from "next/link";
import { SampleTag } from "@/components/ReportView";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { int, usd } from "@/lib/format";

export interface PrFile {
  path: string;
  loc: number;
}

export default function PrPreview({
  title,
  summary,
  files,
  sandboxLine,
  sample = false,
  backHref,
  action,
}: {
  title: string;
  summary: string;
  files: PrFile[];
  sandboxLine: string;
  sample?: boolean;
  backHref: string;
  action?: React.ReactNode;
}) {
  return (
    <div>
      <h1 className="text-3xl font-semibold tracking-tight">
        {title}
        {sample && <SampleTag />}
      </h1>
      <p className="mt-3 font-mono text-sm tabular-nums text-ink-soft">
        {summary}
      </p>

      <div className="mt-8 space-y-2">
        {files.map((f) => (
          <details
            key={f.path}
            className="rounded-lg border border-line bg-surface px-4 py-3 transition-colors hover:border-line-2"
          >
            <summary className="cursor-pointer list-none font-mono text-sm">
              <span className="text-clay">-{int(f.loc)}</span>{" "}
              <span className="text-ink">{f.path}</span>
            </summary>
            <p className="mt-2 text-sm text-ink-soft">
              Whole-file deletion. The file has zero incoming edges in the
              dependency graph.
            </p>
          </details>
        ))}
      </div>

      <div className="mt-8 rounded-lg border border-line bg-surface p-6">
        <p className="text-sm">{sandboxLine}</p>
        {action ?? (
          <>
            <Button
              variant="secondary"
              disabled
              title="Sample reports have no repo to open a pull request against"
              className="mt-4"
            >
              Auto-PR runs on live reports
            </Button>
            <p className="mt-3 text-sm text-ink-soft">
              Deletions ship as draft PRs. Nothing is merged without your
              review.
            </p>
          </>
        )}
      </div>

      <p className="mt-8 text-sm text-ink-soft">
        <Link
          href={backHref}
          className={cn(buttonVariants({ variant: "link" }), "px-0")}
        >
          Back to the report
        </Link>
      </p>
    </div>
  );
}
