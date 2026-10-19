"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  analyzeRepo,
  getJob,
  getReport,
  GhostCodeError,
  type JobStatus,
  type Report,
} from "@/lib/api";

// Polls GET /jobs/{id} until the job settles, then loads GET /report/{id}.
export function useReport(id: string) {
  const [job, setJob] = useState<JobStatus | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rerunning, setRerunning] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;
    const stop = () => {
      if (timer.current) clearInterval(timer.current);
      timer.current = null;
    };
    async function tick() {
      try {
        const j = await getJob(id);
        if (cancelled) return;
        setJob(j);
        if (j.status === "done") {
          stop();
          const r = await getReport(id);
          if (!cancelled) setReport(r);
        } else if (j.status === "error") {
          stop();
          setError(
            j.error?.message ?? "The analysis failed. Try another repository.",
          );
        }
      } catch (err) {
        if (cancelled) return;
        stop();
        setError(
          err instanceof GhostCodeError
            ? err.message
            : "Could not load this report.",
        );
      }
    }
    tick();
    timer.current = setInterval(tick, 3000);
    return () => {
      cancelled = true;
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const rerun = useCallback(async (): Promise<string | null> => {
    if (!job || rerunning) return null;
    setRerunning(true);
    try {
      const next = await analyzeRepo(job.repo);
      return next.job_id;
    } catch (err) {
      setError(
        err instanceof GhostCodeError ? err.message : "Could not re-run.",
      );
      setRerunning(false);
      return null;
    }
  }, [job, rerunning]);

  return { job, report, error, rerun, rerunning };
}
