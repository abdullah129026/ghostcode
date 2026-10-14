# GhostCode — Architecture (4 layers)

## Layer 1: Ingestion Engine
Input: GitHub URL (cloned with GitPython) or local repo zip.
Parsing: tree-sitter (not regex), Python + JS/TS grammars. Extracts imports, exports,
function defs, class defs, call sites. Output: normalized symbol table as JSON.

## Layer 2: The Graph (core IP)
NetworkX directed graph. Nodes: files, functions, classes. Edges: imports, calls,
inherits. Entry-point analysis seeds the reachable set (`main.py`, `index.js`,
`__main__` guards, package.json `main`). Nodes with 0 incoming edges after pruning
are **ghost nodes**.

## Layer 3: Analysis Engines (3 scorers)
- **Dead Code Engine:** unreachable nodes, ranked by LOC and blast radius.
- **Debt Engine:** circular imports (simple cycle detection), duplicated logic
  (AST subtree hashing), huge files (>500 LOC).
- **Cost Engine:** heuristic `LOC × $0.50 × complexity factor` → $/year maintenance
  burn per node. LLM pricing pass (Groq) is a stretch goal: it prices, never finds.

## Layer 4: Action Layer
- Next.js dashboard: hero stats, force-graph visualization, sortable file table
  (File | Type | LOC | $ Saved | Risk | Action).
- Auto-PR: PyGithub creates `ghostcode/remove-<name>` branch, deletes ghost files,
  runs the repo's test suite in a sandbox, opens a PR only on green with
  LOC-deleted and $-saved in the body.

## Data flow
`repo URL → clone → tree-sitter parse → symbol JSON → NetworkX graph →
ghost detection → scorers → cost model → report JSON → dashboard / auto-PR`
