import { int } from "@/lib/format";

export default function Stat({
  label,
  value,
  mono = true,
}: {
  label: string;
  value: string | number;
  mono?: boolean;
}) {
  return (
    <div>
      <p
        className={`text-4xl font-semibold tracking-tight tabular-nums ${
          mono ? "font-mono" : ""
        }`}
      >
        {typeof value === "number" ? int(value) : value}
      </p>
      <p className="mt-1 text-sm text-ink-soft">{label}</p>
    </div>
  );
}
