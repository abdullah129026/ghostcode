export default function SiteFooter() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-5xl flex-col gap-2 px-6 py-10 text-sm text-ink-soft">
        <p className="font-semibold text-ink">GhostCode</p>
        <p>
          MIT licensed. Turns dead code into a P&amp;L statement. Built by{" "}
          <a
            href="https://github.com/abdullah129026"
            target="_blank"
            rel="noreferrer"
            className="underline hover:text-ink"
          >
            Muhammad Abdullah Shah
          </a>
          .
        </p>
        <p>
          v1 analyzes public Python and JavaScript/TypeScript repos. Private
          repos, SSO, and team features are on the v2 roadmap.
        </p>
      </div>
    </footer>
  );
}
