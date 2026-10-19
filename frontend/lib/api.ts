// Typed client for the GhostCode FastAPI backend (report schema v1).
// API base comes from NEXT_PUBLIC_API_URL; falls back to local dev.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Risk = "LOW" | "MED" | "HIGH";

export interface GhostEntry {
  id?: string;
  path: string;
  ghost_kind: "file" | "symbol";
  kind?: string;
  name?: string;
  reason: string;
  reasons: string[];
  confidence: number;
  risk: Risk;
  loc: number;
  annual_saving_usd: number;
}

export interface ReportSummary {
  files: number;
  total_loc: number;
  ghost_files: number;
  ghost_symbols: number;
  ghost_loc: number;
  annual_burn_usd: number;
  debt: {
    circular_imports: number;
    duplicate_groups: number;
    huge_files: number;
  };
}

export interface Report {
  schema: number;
  generated_at: string;
  repo: string;
  summary: ReportSummary;
  ghosts: GhostEntry[];
  debt: unknown;
  cost_model: unknown;
}

export type JobState = "queued" | "running" | "done" | "error";

export interface JobStatus {
  job_id: string;
  status: JobState;
  repo: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  report_url: string | null;
  error: { code: string; message: string } | null;
}

export interface ApiError {
  code: string;
  message: string;
}

export class GhostCodeError extends Error {
  code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

async function readJson(res: Response): Promise<unknown> {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : {};
  } catch {
    return {};
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, init);
  } catch {
    throw new GhostCodeError(
      "api_unreachable",
      "Could not reach the GhostCode API. Is the backend running?",
    );
  }
  const body = await readJson(res);
  if (!res.ok) {
    const err = (body as { error?: ApiError }).error;
    throw new GhostCodeError(
      err?.code ?? "request_failed",
      err?.message ?? `Request failed with status ${res.status}`,
    );
  }
  return body as T;
}

export function analyzeRepo(repoUrl: string): Promise<{
  job_id: string;
  status: JobState;
  poll_url: string;
}> {
  return request("/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

export function getJob(jobId: string): Promise<JobStatus> {
  return request(`/jobs/${encodeURIComponent(jobId)}`);
}

export function getReport(jobId: string): Promise<Report> {
  return request(`/report/${encodeURIComponent(jobId)}`);
}
