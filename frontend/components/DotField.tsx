"use client";

import { useEffect, useRef } from "react";

/**
 * Mouse-reactive dot field, the signature background from the Living Design
 * Copy, restyled to GhostCode's violet palette. Dots on a 24px grid, 2px at
 * rest; dots within 120px of the cursor swell to 5px and deepen toward the
 * accent, easing back over ~300ms. Canvas-rendered, pauses when the tab is
 * hidden, off below 640px, frozen under reduced motion. Solid fills only,
 * never a gradient. Decorative: content contrast never depends on it.
 */
export default function DotField() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    if (window.matchMedia("(max-width: 639px)").matches) return;
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const GRID = 24;
    const REST_R = 1;
    const HOT_R = 2.5;
    const RADIUS = 120;
    let raf = 0;
    let running = false;
    let width = 0;
    let height = 0;
    let dpr = 1;
    let dots: { x: number; y: number; r: number }[] = [];
    const pointer = { x: -9999, y: -9999 };

    const readColors = () => {
      const cs = getComputedStyle(document.documentElement);
      return {
        dot: cs.getPropertyValue("--dot").trim() || "216 210 238",
        hot: cs.getPropertyValue("--dot-hot").trim() || "109 40 217",
      };
    };

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dots = [];
      for (let y = GRID / 2; y < height; y += GRID) {
        for (let x = GRID / 2; x < width; x += GRID) {
          dots.push({ x, y, r: REST_R });
        }
      }
      draw(readColors());
    };

    const draw = ({ dot, hot }: { dot: string; hot: string }) => {
      ctx.clearRect(0, 0, width, height);
      for (const d of dots) {
        const dx = d.x - pointer.x;
        const dy = d.y - pointer.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        const target =
          dist < RADIUS
            ? REST_R + (HOT_R - REST_R) * (1 - dist / RADIUS)
            : REST_R;
        // Ease toward target; ~300ms settle at 60fps.
        d.r += (target - d.r) * 0.18;
        const heat = Math.min(
          1,
          Math.max(0, (d.r - REST_R) / (HOT_R - REST_R)),
        );
        ctx.beginPath();
        ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
        ctx.fillStyle =
          heat > 0.02
            ? `rgba(${hot} / ${0.25 + 0.75 * heat})`
            : `rgb(${dot})`;
        ctx.fill();
      }
    };

    const tick = () => {
      if (!running) return;
      draw(readColors());
      raf = requestAnimationFrame(tick);
    };

    const start = () => {
      if (running || document.hidden) return;
      running = true;
      raf = requestAnimationFrame(tick);
    };
    const stop = () => {
      running = false;
      cancelAnimationFrame(raf);
    };

    const onMove = (e: PointerEvent) => {
      pointer.x = e.clientX;
      pointer.y = e.clientY;
    };
    const onLeave = () => {
      pointer.x = -9999;
      pointer.y = -9999;
    };
    const onVisibility = () => {
      if (document.hidden) stop();
      else start();
    };

    resize();
    if (!reduced) {
      start();
      window.addEventListener("pointermove", onMove, { passive: true });
      window.addEventListener("pointerleave", onLeave);
      document.addEventListener("visibilitychange", onVisibility);
    }
    window.addEventListener("resize", resize);

    return () => {
      stop();
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("resize", resize);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 hidden sm:block"
    />
  );
}
