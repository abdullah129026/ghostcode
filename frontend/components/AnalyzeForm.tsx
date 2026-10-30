"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { analyzeRepo, GhostCodeError } from "@/lib/api";

export default function AnalyzeForm() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    // A disabled submit button does not stop Enter-key resubmission, so
    // guard here too: one in-flight request means one job, not two.
    if (busy) return;
    setError(null);
    setBusy(true);
    try {
      const job = await analyzeRepo(url.trim());
      router.push(`/report/${job.job_id}`);
    } catch (err) {
      setError(
        err instanceof GhostCodeError
          ? err.message
          : "Something went wrong starting the analysis.",
      );
      setBusy(false);
    }
  }

  return (
    <div>
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <input
          type="url"
          required
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://github.com/your-org/your-repo"
          aria-label="GitHub repository URL"
          className="w-full rounded-md border border-line bg-white px-4 py-3 font-mono text-sm placeholder:text-ink-soft/60 focus:border-moss focus:outline-none"
        />
        <button
          type="submit"
          disabled={busy}
          className="shrink-0 rounded-md bg-moss px-6 py-3 font-medium text-white hover:bg-moss-deep disabled:opacity-60"
        >
          {busy ? "Starting..." : "Analyze this repo"}
        </button>
      </form>
      {error && (
        <p role="alert" className="mt-3 text-sm text-clay">
          {error}
        </p>
      )}
      <p className="mt-3 text-sm text-ink-soft">
        Free for public repos. No credit card required.{" "}
        <Link href="/report/sample" className="underline hover:text-ink">
          See a sample report
        </Link>
      </p>
    </div>
  );
}
