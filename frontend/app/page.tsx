import Link from "next/link";
import SiteHeader from "@/components/SiteHeader";
import SiteFooter from "@/components/SiteFooter";
import AnalyzeForm from "@/components/AnalyzeForm";

const STEPS = [
  {
    title: "Paste a GitHub URL.",
    body: "Any public Python or JavaScript/TypeScript repo. No install, no tokens.",
  },
  {
    title: "We parse every file into a dependency graph.",
    body: "Tree-sitter parsing, per-function chunking, zero-incoming-edge ghost detection.",
  },
  {
    title: "You get the burn number and the safe deletes.",
    body: "Annual cost in dollars, ranked files, and PRs your own test suite has already approved in a sandbox.",
  },
];

const TRUST = [
  "Your code is never used to train models.",
  "Ephemeral clones: deleted after every analysis.",
  "Public repos are free to analyze, forever.",
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <SiteHeader />
      <main>
        <section id="analyze" className="mx-auto max-w-5xl px-6 pb-20 pt-16">
          <p className="text-sm font-medium uppercase tracking-widest text-ink-soft">
            Dead-code analysis for Python and JavaScript
          </p>
          <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-tight tracking-tight">
            Your dead code costs $4,200 a year. Here is the receipt.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-ink-soft">
            GhostCode maps your repository&apos;s dependency graph, finds the
            code nothing calls, and prices it in dollars per year. Then it opens
            the pull requests that delete it safely.
          </p>
          <div className="mt-8 max-w-2xl">
            <AnalyzeForm />
          </div>
        </section>

        <section
          id="how-it-works"
          className="border-t border-line bg-white"
        >
          <div className="mx-auto max-w-5xl px-6 py-16">
            <h2 className="text-2xl font-semibold tracking-tight">
              How it works
            </h2>
            <ol className="mt-8 grid gap-10 md:grid-cols-3">
              {STEPS.map((s, i) => (
                <li key={s.title}>
                  <p className="font-mono text-sm text-moss">0{i + 1}</p>
                  <h3 className="mt-2 font-semibold">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-ink-soft">
                    {s.body}
                  </p>
                </li>
              ))}
            </ol>
            <div className="mt-12 rounded-lg border border-line bg-paper p-6">
              <p className="text-xs font-medium uppercase tracking-widest text-ink-soft">
                Sample report: old-shop-api
              </p>
              <div className="mt-3 flex flex-wrap gap-x-10 gap-y-2 font-mono text-sm tabular-nums">
                <span>18% ghost code</span>
                <span>$4,200/yr est. burn</span>
                <span>3 safe-to-delete PRs</span>
              </div>
              <Link
                href="/report/sample"
                className="mt-4 inline-block text-sm font-medium text-moss-deep underline"
              >
                Open the sample report
              </Link>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-5xl px-6 py-16">
          <h2 className="text-2xl font-semibold tracking-tight">
            Free for open source, forever.
          </h2>
          <p className="mt-4 max-w-2xl leading-relaxed text-ink-soft">
            GhostCode is MIT licensed, and public repos are always free to
            analyze. Read the code, run it yourself, send a PR.
          </p>
          <div className="mt-6 flex flex-wrap gap-6">
            <a
              href="https://github.com/abdullah129026/ghostcode"
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-line bg-white px-5 py-2.5 text-sm font-medium hover:border-ink"
            >
              Star on GitHub
            </a>
          </div>
          <ul className="mt-10 space-y-2 text-sm text-ink-soft">
            {TRUST.map((t) => (
              <li key={t} className="flex gap-2">
                <span aria-hidden className="text-moss">
                  ✓
                </span>
                {t}
              </li>
            ))}
          </ul>
        </section>
      </main>
      <SiteFooter />
    </div>
  );
}
