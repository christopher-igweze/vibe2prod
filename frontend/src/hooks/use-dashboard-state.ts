"use client";

import { useState, useEffect, useMemo } from "react";
import { apiFetch, sanitizeFilename } from "@/lib/api/client";
import { computeDashboardMetrics } from "@/app/(app)/dashboard/_components/dashboard-utils";
import type { DiscoveryReport, ProjectSummary, ProbeSummary } from "@/lib/api/types";
import type { ScanSummary } from "@/components/dashboard/scan-row";

interface ScanDetail {
  id: string;
  report_data?: {
    discovery_report?: DiscoveryReport;
  };
}

function downloadReportJson(report: DiscoveryReport, repoName: string) {
  const slug = sanitizeFilename((repoName || "repo").replace(/\//g, "-"));
  const date = new Date().toISOString().slice(0, 10);
  const filename = `forge-report-${slug}-${date}.json`;
  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function useDashboardState(getToken: () => Promise<string | null>) {
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [probes, setProbes] = useState<ProbeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [copyingId, setCopyingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const metrics = useMemo(() => computeDashboardMetrics(scans), [scans]);

  const projectScanMap = useMemo(() => {
    const map = new Map<string, ScanSummary[]>();
    for (const scan of scans) {
      const key = scan.project_id || scan.repo_url;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(scan);
    }
    return map;
  }, [scans]);

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined;
        const [s, p, pr] = await Promise.all([
          apiFetch<ScanSummary[] | { items: ScanSummary[] }>("/api/user/scans", { token }).then(r => Array.isArray(r) ? r : r.items ?? []).catch(() => [] as ScanSummary[]),
          apiFetch<ProjectSummary[] | { items: ProjectSummary[] }>("/api/user/projects", { token }).then(r => Array.isArray(r) ? r : r.items ?? []).catch(() => [] as ProjectSummary[]),
          apiFetch<ProbeSummary[]>("/api/user/probes", { token }).catch(() => [] as ProbeSummary[]),
        ]);
        setScans(s);
        setProjects(p);
        setProbes(pr);
      } catch {
        setError("Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [getToken]);

  async function handleDownload(scan: ScanSummary) {
    setDownloadingId(scan.id);
    try {
      const token = (await getToken()) ?? undefined;
      const detail = await apiFetch<ScanDetail>(
        `/api/user/scans/${scan.id}`,
        { token },
      );
      const report = detail.report_data?.discovery_report;
      if (report) {
        downloadReportJson(report, scan.repo_name || scan.repo_url);
      }
    } catch {
      setError("Failed to download report");
    } finally {
      setDownloadingId(null);
    }
  }

  async function handleCopy(scan: ScanSummary) {
    setCopyingId(scan.id);
    try {
      const token = (await getToken()) ?? undefined;
      const detail = await apiFetch<ScanDetail>(
        `/api/user/scans/${scan.id}`,
        { token },
      );
      const report = detail.report_data?.discovery_report;
      if (report) {
        await navigator.clipboard.writeText(JSON.stringify(report, null, 2));
        setCopiedId(scan.id);
        setTimeout(() => setCopiedId(null), 2000);
      }
    } catch {
      // Silently fail
    } finally {
      setCopyingId(null);
    }
  }

  async function handleDelete(scanId: string) {
    setDeletingId(scanId);
    try {
      const token = (await getToken()) ?? undefined;
      await apiFetch(`/api/user/scans/${scanId}`, {
        method: "DELETE",
        token,
      });
      setScans((prev) => prev.filter((s) => s.id !== scanId));
    } catch {
      setError("Failed to delete scan");
    } finally {
      setDeletingId(null);
    }
  }

  return {
    scans,
    projects,
    probes,
    loading,
    error,
    metrics,
    projectScanMap,
    downloadingId,
    deletingId,
    copyingId,
    copiedId,
    handleDownload,
    handleCopy,
    handleDelete,
  };
}
