import Link from "next/link";

export default function ReportTabs({
  base,
  active,
}: {
  base: string;
  active: "report" | "graph" | "files";
}) {
  const tabs = [
    { key: "report", label: "Report", href: base },
    { key: "graph", label: "Graph view", href: `${base}/graph` },
    { key: "files", label: "File table", href: `${base}/files` },
  ] as const;
  return (
    <nav className="flex gap-1 border-b border-line" aria-label="Report views">
      {tabs.map((t) => (
        <Link
          key={t.key}
          href={t.href}
          aria-current={active === t.key ? "page" : undefined}
          className={`-mb-px border-b-2 px-4 py-2 text-sm font-medium ${
            active === t.key
              ? "border-moss text-ink"
              : "border-transparent text-ink-soft hover:text-ink"
          }`}
        >
          {t.label}
        </Link>
      ))}
    </nav>
  );
}
