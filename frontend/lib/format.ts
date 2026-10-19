// Money and number formatting: tabular numerals, no invented precision.

export function usd(n: number): string {
  return "$" + Math.round(n).toLocaleString("en-US");
}

export function int(n: number): string {
  return Math.round(n).toLocaleString("en-US");
}

export function pct(numerator: number, denominator: number): string {
  if (!denominator) return "0%";
  return Math.round((numerator / denominator) * 100) + "%";
}

export function riskLabel(risk: "LOW" | "MED" | "HIGH"): string {
  return { LOW: "low", MED: "medium", HIGH: "high" }[risk];
}

export function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? "" : "s"} ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? "" : "s"} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"} ago`;
}
