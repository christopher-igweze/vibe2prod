"use client";

export const dynamic = "force-dynamic";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { Download, Trash2, Loader2, Copy, Check, RefreshCw, ChevronRight } from "lucide-react";
import { apiFetch } from "@/lib/api/client";
import { useUserRole } from "@/hooks/use-user-role";
import { useTour } from "@/components/tour/tour-provider";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { DiscoveryReport, ProjectSummary } from "@/lib/api/types";
import { computeDashboardMetrics, scoreColorClass } from "./_components/dashboard-utils";
import { DashboardStats } from "./_components/dashboard-stats";
import { DashboardInsights } from "./_components/dashboard-insights";

interface ScanSummary {
  id: string;
  repo_url: string;
  repo_name: string;
  status: string;
  scan_tier: string | null;
  created_at: string;
  project_id: string | null;
  health_score: number | null;
  security_score: number | null;
  reliability_score: number | null;
  scalability_score: number | null;
}

interface ScanDetail {
  id: string;
  report_data?: {
    discovery_report?: DiscoveryReport;
  };
}

function downloadReportJson(report: DiscoveryReport, repoName: string) {
  const slug = (repoName || "repo").replace(/\//g, "-");
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

// ---------------------------------------------------------------------------
// Scan row with actions (reused inside project cards)
// ---------------------------------------------------------------------------

function ScanRow({
  scan,
  downloadingId,
  deletingId,
  copyingId,
  copiedId,
  onDownload,
  onCopy,
  onDelete,
}: {
  scan: ScanSummary;
  downloadingId: string | null;
  deletingId: string | null;
  copyingId: string | null;
  copiedId: string | null;
  onDownload: (scan: ScanSummary) => void;
  onCopy: (scan: ScanSummary) => void;
  onDelete: (scanId: string) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg hover:bg-white/[0.02] transition-colors">
      <Link
        href={scan.status === "completed" ? `/scan/${scan.id}/report` : `/scan/${scan.id}`}
        className="flex-1 min-w-0"
      >
        <div className="cursor-pointer flex items-center gap-3">
          <div className="min-w-0">
            <p className="text-sm text-[#E8ECF4] truncate">
              {new Date(scan.created_at).toLocaleDateString()}
              {scan.scan_tier && <span className="text-[#4E586E] ml-2">{scan.scan_tier}</span>}
            </p>
            {scan.health_score !== null && (
              <p className="text-xs mt-0.5">
                <span className={scoreColorClass(scan.health_score)}>
                  Health: {scan.health_score}
                </span>
              </p>
            )}
          </div>
        </div>
      </Link>

      <div className="flex items-center gap-1 shrink-0">
        {scan.status === "completed" && (
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-[#8692A8] hover:text-forge-emerald"
            disabled={copyingId === scan.id}
            onClick={() => onCopy(scan)}
          >
            {copyingId === scan.id ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : copiedId === scan.id ? (
              <Check className="size-3.5 text-forge-emerald" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </Button>
        )}

        {scan.status === "completed" && (
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-[#8692A8] hover:text-forge-emerald"
            disabled={downloadingId === scan.id}
            onClick={() => onDownload(scan)}
          >
            {downloadingId === scan.id ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Download className="size-3.5" />
            )}
          </Button>
        )}

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 text-[#4E586E] hover:text-red-400"
              disabled={deletingId === scan.id}
            >
              {deletingId === scan.id ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Trash2 className="size-3.5" />
              )}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Delete this scan?</AlertDialogTitle>
              <AlertDialogDescription className="text-[#8692A8]">
                This will permanently delete the scan for{" "}
                <span className="font-medium text-neutral-300">
                  {scan.repo_name || scan.repo_url}
                </span>
                . This action cannot be undone.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => onDelete(scan.id)}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <Badge
          className="ml-1 text-[10px]"
          variant={
            scan.status === "completed"
              ? "default"
              : scan.status === "failed"
              ? "destructive"
              : "secondary"
          }
        >
          {scan.status}
        </Badge>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main dashboard
// ---------------------------------------------------------------------------

export default function DashboardPage() {
  const { getToken } = useAuth();
  const { role, profile } = useUserRole();
  const { startTour } = useTour();
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [copyingId, setCopyingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const metrics = useMemo(() => computeDashboardMetrics(scans), [scans]);

  // Group scans by project_id
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
        const [s, p] = await Promise.all([
          apiFetch<ScanSummary[]>("/api/user/scans", { token }).catch(() => [] as ScanSummary[]),
          apiFetch<ProjectSummary[]>("/api/user/projects", { token }).catch(() => [] as ProjectSummary[]),
        ]);
        setScans(s);
        setProjects(p);
      } catch {
        setError("Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [getToken]);

  // Auto-trigger tour after onboarding
  useEffect(() => {
    if (!loading && profile?.onboarding_complete && profile?.tour_completed === false) {
      const timer = setTimeout(() => startTour("/dashboard"), 800);
      return () => clearTimeout(timer);
    }
  }, [loading, profile, startTour]);

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
    } finally {
      setDeletingId(null);
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-forge-nav rounded animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-forge-nav rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)]">Dashboard</h1>
        <Link href="/scan/new" data-tour="new-scan-btn">
          <Button className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
            New Scan
          </Button>
        </Link>
      </div>

      {role === "developer" ? (
        <div className="text-sm text-forge-emerald">Unlimited Scans</div>
      ) : (profile?.balance_usd ?? 0) <= 0 ? (
        <Card className="border-amber-500/30 bg-amber-500/5 p-4">
          <div className="flex items-center justify-between">
            <p className="text-amber-400 text-sm font-medium">Wallet balance is $0.00</p>
            <Link href="/pricing">
              <Button size="sm" className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
                Add Funds
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-[#8692A8]">
            Balance: <span className="text-forge-emerald font-semibold">${(profile?.balance_usd ?? 0).toFixed(2)}</span>
          </span>
          <Link href="/pricing" className="text-forge-emerald hover:text-forge-emerald-light underline text-xs">
            Add Funds
          </Link>
        </div>
      )}

      {error && (
        <Card className="border-red-500/50 bg-red-950/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </Card>
      )}

      {scans.length > 0 && (
        <div data-tour="stats-panel">
          <DashboardStats metrics={metrics} />
          <DashboardInsights metrics={metrics} />
        </div>
      )}

      {scans.length === 0 ? (
        <Card className="border-dashed p-12 text-center" data-tour="scan-list">
          <h2 className="text-lg font-semibold mb-2">No scans yet</h2>
          <p className="text-[#8692A8] text-sm mb-6">
            Paste a GitHub URL to run your first audit.
          </p>
          <Link href="/scan/new">
            <Button className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
              Start Your First Scan
            </Button>
          </Link>
        </Card>
      ) : projects.length > 0 ? (
        /* Grouped by project */
        <div className="space-y-4" data-tour="scan-list">
          <h2 className="text-lg font-semibold">Projects</h2>
          {projects.map((project) => {
            const projectScans = (projectScanMap.get(project.id) || []).slice(0, 3);
            const displayName = project.repo_name || project.repo_url;
            const repoUrlEncoded = encodeURIComponent(project.repo_url);

            return (
              <Card key={project.id} className="forge-glass-card p-0 overflow-hidden">
                {/* Project header */}
                <div className="flex items-center justify-between gap-3 p-4 border-b border-white/[0.06]">
                  <Link href={`/project/${project.id}`} className="flex-1 min-w-0 group">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-[#E8ECF4] truncate group-hover:text-forge-emerald transition-colors">
                        {displayName}
                      </h3>
                      <ChevronRight className="size-4 text-[#4E586E] shrink-0 group-hover:text-forge-emerald transition-colors" />
                    </div>
                    <div className="flex items-center gap-3 mt-1 text-xs text-[#8692A8]">
                      <span>{project.scan_count} scan{project.scan_count !== 1 ? "s" : ""}</span>
                      {project.latest_health_score !== null && (
                        <span className={scoreColorClass(project.latest_health_score)}>
                          Health: {project.latest_health_score}
                        </span>
                      )}
                    </div>
                  </Link>

                  <Link href={`/scan/new?repo_url=${repoUrlEncoded}`}>
                    <Button size="sm" variant="ghost" className="text-[#8692A8] hover:text-forge-emerald gap-1.5">
                      <RefreshCw className="size-3.5" /> Re-scan
                    </Button>
                  </Link>
                </div>

                {/* Recent scans for this project */}
                {projectScans.length > 0 && (
                  <div className="divide-y divide-white/[0.04]">
                    {projectScans.map((scan) => (
                      <ScanRow
                        key={scan.id}
                        scan={scan}
                        downloadingId={downloadingId}
                        deletingId={deletingId}
                        copyingId={copyingId}
                        copiedId={copiedId}
                        onDownload={handleDownload}
                        onCopy={handleCopy}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                )}
              </Card>
            );
          })}

          {/* Ungrouped scans (no project_id) */}
          {(() => {
            const projectIds = new Set(projects.map((p) => p.id));
            const ungrouped = scans.filter((s) => !s.project_id || !projectIds.has(s.project_id));
            if (ungrouped.length === 0) return null;
            return (
              <>
                <h2 className="text-lg font-semibold mt-6">Other Scans</h2>
                <div className="space-y-3">
                  {ungrouped.map((scan) => (
                    <Card key={scan.id} className="forge-glass-hover p-0 transition-colors">
                      <ScanRow
                        scan={scan}
                        downloadingId={downloadingId}
                        deletingId={deletingId}
                        copyingId={copyingId}
                        copiedId={copiedId}
                        onDownload={handleDownload}
                        onCopy={handleCopy}
                        onDelete={handleDelete}
                      />
                    </Card>
                  ))}
                </div>
              </>
            );
          })()}
        </div>
      ) : (
        /* Fallback: flat list when no projects returned */
        <div className="space-y-3" data-tour="scan-list">
          <h2 className="text-lg font-semibold">Recent Scans</h2>
          {scans.map((scan) => (
            <Card
              key={scan.id}
              className="forge-glass-hover p-0 transition-colors"
            >
              <ScanRow
                scan={scan}
                downloadingId={downloadingId}
                deletingId={deletingId}
                copyingId={copyingId}
                copiedId={copiedId}
                onDownload={handleDownload}
                onCopy={handleCopy}
                onDelete={handleDelete}
              />
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
