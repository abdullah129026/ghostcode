"use client";

import { useEffect, useRef, useState } from "react";
import { int, usd } from "@/lib/format";

// Animated data: numeric stats count up to their final value on mount
// (700ms ease-out). String values render as-is. Reduced motion renders
// the final value immediately; the number never depends on the animation.
// format is a key, not a function, so server components can pass it.
const FORMATS = { int, usd } as const;

export default function Stat({
  label,
  value,
  mono = true,
  format = "int",
}: {
  label: string;
  value: string | number;
  mono?: boolean;
  format?: keyof typeof FORMATS;
}) {
  const target = typeof value === "number" ? value : null;
  const [shown, setShown] = useState(target ?? 0);
  const rafRef = useRef(0);

  useEffect(() => {
    if (target === null) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setShown(target);
      return;
    }
    const start = performance.now();
    const duration = 700;
    const tick = (now: number) => {
      const p = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      setShown(Math.round(target * eased));
      if (p < 1) rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [target]);

  const text =
    target === null ? value : FORMATS[format](shown);

  return (
    <div>
      <p
        className={`text-4xl font-semibold tracking-tight tabular-nums ${
          mono ? "font-mono" : ""
        }`}
      >
        {text}
      </p>
      <p className="mt-1 text-sm text-ink-soft">{label}</p>
    </div>
  );
}
