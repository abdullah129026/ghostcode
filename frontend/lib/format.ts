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
