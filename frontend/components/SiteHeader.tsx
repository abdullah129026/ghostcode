import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="text-lg font-semibold tracking-tight">
          GhostCode
        </Link>
        <nav className="flex items-center gap-6 text-sm text-ink-soft">
          <Link href="/#how-it-works" className="hover:text-ink">
            How it works
          </Link>
          <Link href="/report/sample" className="hover:text-ink">
            Sample report
          </Link>
          <a
            href="https://github.com/abdullah129026/ghostcode"
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink"
          >
            GitHub
          </a>
          <Link
            href="/#analyze"
            className="rounded-md bg-moss px-4 py-2 font-medium text-white hover:bg-moss-deep"
          >
            Analyze a repo
          </Link>
        </nav>
      </div>
    </header>
  );
}
