"use client";

import { useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { GraphNode, ReportGraph } from "@/lib/api";

const GHOST = "#059669";
const HEALTHY = "#1C1917";
const HEALTHY_DIM = "rgba(28, 25, 23, 0.12)";
const LINK = "#D6D3D1";

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
          className="rounded-md border border-line bg-white px-3 py-1.5 text-sm font-medium hover:border-ink"
        >
          Fit
        </button>
        <button
          onClick={() => onSelect(null)}
          className="rounded-md border border-line bg-white px-3 py-1.5 text-sm font-medium hover:border-ink"
        >
          Clear selection
        </button>
      </div>
      <div className="absolute bottom-4 left-4 z-10 flex gap-4 rounded-md border border-line bg-white px-4 py-2 text-xs text-ink-soft">
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-2.5 rounded-full bg-moss" />
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
        backgroundColor="#FDFCFB"
        nodeColor={(n: FGNode) =>
          n.ghost ? GHOST : ghostOnly ? HEALTHY_DIM : HEALTHY
        }
        nodeVal={(n: FGNode) => 2 + Math.sqrt(n.loc) / 6}
        nodeLabel={(n: FGNode) => `${n.path} (${n.loc} LOC)`}
        nodeCanvasObjectMode={() => "after"}
        nodeCanvasObject={(n: FGNode, ctx: CanvasRenderingContext2D) => {
          if (hover !== n.id && !n.ghost) return;
          ctx.font = "11px 'JetBrains Mono', monospace";
          ctx.fillStyle = "#1C1917";
          ctx.fillText(n.path, (n.x ?? 0) + 8, (n.y ?? 0) + 4);
        }}
        onNodeHover={(n: FGNode | null) => setHover(n ? n.id : null)}
        onNodeClick={(n: FGNode) => onSelect(n)}
        onBackgroundClick={() => onSelect(null)}
        linkColor={() => LINK}
        linkWidth={1}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
      />
    </div>
  );
}
