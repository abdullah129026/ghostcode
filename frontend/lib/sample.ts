// Sample report for the fictional repo "old-shop-api".
// Source of truth: ghostcode-full-design.md section 2. Demo data only:
// every page that renders it carries a "Sample report" tag so it is never
// mistaken for a measured result.
import type { Report } from "./api";

export const SAMPLE_REPORT_ID = "sample";

export const sampleReport: Report = {
  schema: 2,
  generated_at: "2026-10-19T04:00:00Z",
  repo: "old-shop-api",
  summary: {
    files: 412,
    total_loc: 68200,
    ghost_files: 3,
    ghost_symbols: 2,
    ghost_loc: 12276,
    annual_burn_usd: 4200,
    debt: { circular_imports: 2, duplicate_groups: 4, huge_files: 6 },
  },
  ghosts: [
    {
      path: "utils/legacy_billing.py",
      ghost_kind: "file",
      reason: "no incoming imports and not an entry point",
      reasons: [
        "no incoming imports and not an entry point",
        "entire file is unreferenced, deletes as one unit",
      ],
      confidence: 0.97,
      risk: "LOW",
      loc: 1840,
      annual_saving_usd: 620,
    },
    {
      path: "services/reporting/v1/",
      ghost_kind: "file",
      reason: "no incoming imports and not an entry point",
      reasons: [
        "no incoming imports and not an entry point",
        "entire file is unreferenced, deletes as one unit",
      ],
      confidence: 0.92,
      risk: "LOW",
      loc: 1220,
      annual_saving_usd: 410,
    },
    {
      path: "api/deprecated_endpoints.py",
      ghost_kind: "file",
      reason: "no incoming imports and not an entry point",
      reasons: [
        "no incoming imports and not an entry point",
        "entire file is unreferenced, deletes as one unit",
      ],
      confidence: 0.9,
      risk: "LOW",
      loc: 980,
      annual_saving_usd: 330,
    },
    {
      path: "invoices.py",
      ghost_kind: "symbol",
      kind: "function",
      name: "format_invoice",
      reason: "no incoming calls or named imports",
      reasons: ["no incoming calls or named imports"],
      confidence: 0.66,
      risk: "MED",
      loc: 210,
      annual_saving_usd: 71,
    },
  ],
  debt: {
    circular_imports: { cycles: [["a.py", "b.py"], ["c.py", "d.py"]] },
    duplicates: [{}, {}, {}, {}],
    huge_files: [{}, {}, {}, {}, {}, {}],
  },
  graph: {
    nodes: [
      { id: "file:app.py", path: "app.py", loc: 420, ghost: false },
      { id: "file:api/routes.py", path: "api/routes.py", loc: 890, ghost: false },
      {
        id: "file:api/deprecated_endpoints.py",
        path: "api/deprecated_endpoints.py",
        loc: 980,
        ghost: true,
      },
      {
        id: "file:utils/legacy_billing.py",
        path: "utils/legacy_billing.py",
        loc: 1840,
        ghost: true,
      },
      { id: "file:utils/money.py", path: "utils/money.py", loc: 310, ghost: false },
      {
        id: "file:services/reporting/v1/",
        path: "services/reporting/v1/",
        loc: 1220,
        ghost: true,
      },
      {
        id: "file:services/reporting/v2.py",
        path: "services/reporting/v2.py",
        loc: 760,
        ghost: false,
      },
    ],
    edges: [
      { source: "file:app.py", target: "file:api/routes.py" },
      { source: "file:api/routes.py", target: "file:utils/money.py" },
      { source: "file:api/routes.py", target: "file:services/reporting/v2.py" },
    ],
    truncated: false,
  },
  cost_model: {
    params: { cost_per_loc: 0.5 },
    llm_pricing: { model: "groq/llama-3.3-70b-versatile" },
  },
};

export function getSampleReport(): Report {
  return sampleReport;
}
