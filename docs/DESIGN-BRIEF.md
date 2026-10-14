# GhostCode — Design Brief (compact)

One screen, one argument: "your dead code costs $X/year, here are the safe deletes."

## Layout
- **Hero stat band:** three huge numbers — Ghost LOC, Est. annual burn ($), Safe PRs.
  Fraunces-style serif numerals or heavy tabular sans; no tiny stat cards.
- **Graph view:** react-force-graph, ghost nodes in red/orange, healthy in neutral.
  Dark-on-light or light-on-dark, whichever reads better; keep it legible, not neon.
- **File table:** File | Type | LOC | $ Saved | Risk | Action. Risk as text pill
  (LOW/MED/HIGH), Action as a plain "Open PR" button. Sortable by $ Saved default.

## Rules
- Inter for all UI text, loaded properly.
- No gradients, no glassmorphism, no emoji icons, no AI-slop card grids.
- Whitespace over density: one idea per panel.
- Every number on screen must come from a real analysis run, never a placeholder.
