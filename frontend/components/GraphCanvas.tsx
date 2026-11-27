"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphNode, ReportGraph } from "@/lib/api";

// Canvas colors come from the design tokens, never hardcoded hex: the
// graph re-reads them when the theme class flips, so ghost nodes stay
// violet and healthy nodes stay ink in light and dark.
function useGraphColors() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    const el = document.documentElement;
    const update = () => setDark(el.classList.contains("dark"));
    update();
    const obs = new MutationObserver(update);
    obs.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => obs.disconnect();
  }, []);
  return useMemo(() => {
    const cs = getComputedStyle(document.documentElement);
    const triplet = (name: string, fallback: string) =>
      cs.getPropertyValue(name).trim() || fallback;
    const accent = triplet("--accent", "109 40 217");
    const ink = triplet("--ink", "28 25 23");
    const line = triplet("--line", "231 224 214");
    const surface = triplet("--surface", "255 255 255");
    return {
      ghost: `rgb(${accent})`,
      healthy: `rgb(${ink})`,
      healthyDim: `rgba(${ink} / 0.12)`,
      link: `rgb(${line})`,
      background: `rgb(${surface})`,
      label: `rgb(${ink})`,
    };
  }, [dark]);
}

interface FGNode extends GraphNode {
  x?: number;
  y?: number;
}

export default function GraphCanvas({
  graph,
  ghostOnly,
  onSelect,
}: {
  graph: ReportGraph;
  ghostOnly: boolean;
  onSelect: (node: GraphNode | null) => void;
}) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ref = useRef<any>(null);
  const [hover, setHover] = useState<string | null>(null);
  const colors = useGraphColors();

  const data = useMemo(
    () => ({
      nodes: graph.nodes.map((n) => ({ ...n })),
      links: graph.edges.map((e) => ({ ...e })),
    }),
    [graph],
  );

  return (
    <div className="relative">
      <div className="absolute left-4 top-4 z-10 flex gap-2">
        <button
          onClick={() => ref.current?.zoomToFit(400)}
          className="rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium transition-colors hover:border-ink"
        >
          Fit
        </button>
        <button
          onClick={() => onSelect(null)}
          className="rounded-md border border-line bg-surface px-3 py-1.5 text-sm font-medium transition-colors hover:border-ink"
        >
          Clear selection
        </button>
      </div>
      <div className="absolute bottom-4 left-4 z-10 flex gap-4 rounded-md border border-line bg-surface px-4 py-2 text-xs text-ink-soft">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-accent" />
          Ghost: 0 incoming edges
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-ink" />
          Healthy
        </span>
      </div>
      <ForceGraph2D
        ref={ref}
        graphData={data}
        height={620}
        backgroundColor={colors.background}
        nodeColor={(n: FGNode) =>
          n.ghost ? colors.ghost : ghostOnly ? colors.healthyDim : colors.healthy
        }
        nodeVal={(n: FGNode) => 2 + Math.sqrt(n.loc) / 6}
        nodeLabel={(n: FGNode) => `${n.path} (${n.loc} LOC)`}
        nodeCanvasObjectMode={() => "after"}
        nodeCanvasObject={(n: FGNode, ctx: CanvasRenderingContext2D) => {
          if (hover !== n.id && !n.ghost) return;
          ctx.font = "11px 'JetBrains Mono', monospace";
          ctx.fillStyle = colors.label;
          ctx.fillText(n.path, (n.x ?? 0) + 8, (n.y ?? 0) + 4);
        }}
        onNodeHover={(n: FGNode | null) => setHover(n ? n.id : null)}
        onNodeClick={(n: FGNode) => onSelect(n)}
        onBackgroundClick={() => onSelect(null)}
        linkColor={() => colors.link}
        linkWidth={1}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
    </div>
  );
}
