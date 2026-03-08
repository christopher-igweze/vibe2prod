"use client";

export const dynamic = "force-dynamic";

import { useEffect, useMemo, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { Download, Trash2, Loader2, Copy, Check } from "lucide-react";
import { apiFetch } from "@/lib/api/client";
import { useUserRole } from "@/hooks/use-user-role";
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
import type { DiscoveryReport } from "@/lib/api/types";
import { computeDashboardMetrics } from "./_components/dashboard-utils";
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

export default function DashboardPage() {
  const { getToken } = useAuth();
  const { role, profile } = useUserRole();
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [copyingId, setCopyingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const metrics = useMemo(() => computeDashboardMetrics(scans), [scans]);

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined;
        const s = await apiFetch<ScanSummary[]>("/api/user/scans", { token }).catch(() => [] as ScanSummary[]);
        setScans(s);
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
        <Link href="/scan/new">
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
        <>
          <DashboardStats metrics={metrics} />
          <DashboardInsights metrics={metrics} />
        </>
      )}

      {scans.length === 0 ? (
        <Card className="border-dashed p-12 text-center">
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
      ) : (
        <div className="space-y-3">
          <h2 className="text-lg font-semibold">Recent Scans</h2>
          {scans.map((scan) => (
            <Card
              key={scan.id}
              className="forge-glass-hover p-4 transition-colors"
            >
              <div className="flex items-center justify-between gap-3">
                <Link
                  href={scan.status === "completed" ? `/scan/${scan.id}/report` : `/scan/${scan.id}`}
                  className="flex-1 min-w-0"
                >
                  <div className="cursor-pointer">
                    <p className="font-medium truncate">{scan.repo_name || scan.repo_url}</p>
                    <p className="text-xs text-[#4E586E] mt-1">
                      {new Date(scan.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </Link>

                <div className="flex items-center gap-2 shrink-0">
                  {scan.status === "completed" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-[#8692A8] hover:text-forge-emerald"
                      disabled={copyingId === scan.id}
                      onClick={() => handleCopy(scan)}
                    >
                      {copyingId === scan.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : copiedId === scan.id ? (
                        <Check className="size-4 text-forge-emerald" />
                      ) : (
                        <Copy className="size-4" />
                      )}
                    </Button>
                  )}

                  {scan.status === "completed" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-[#8692A8] hover:text-forge-emerald"
                      disabled={downloadingId === scan.id}
                      onClick={() => handleDownload(scan)}
                    >
                      {downloadingId === scan.id ? (
                        <Loader2 className="size-4 animate-spin" />
                      ) : (
                        <Download className="size-4" />
                      )}
                    </Button>
                  )}

                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-8 text-[#4E586E] hover:text-red-400"
                        disabled={deletingId === scan.id}
                      >
                        {deletingId === scan.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <Trash2 className="size-4" />
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
                        <AlertDialogCancel>
                          Cancel
                        </AlertDialogCancel>
                        <AlertDialogAction
                          onClick={() => handleDelete(scan.id)}
                          className="bg-red-600 hover:bg-red-700 text-white"
                        >
                          Delete
                        </AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>

                  <Badge
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
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
