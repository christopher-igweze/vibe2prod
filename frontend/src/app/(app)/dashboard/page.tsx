"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { Download, Trash2, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api/client";
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

interface ScanSummary {
  id: string;
  repo_url: string;
  repo_name: string;
  status: string;
  created_at: string;
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
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

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
        <div className="h-8 w-48 bg-neutral-800 rounded animate-pulse" />
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 bg-neutral-800 rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <Link href="/scan/new">
          <Button className="bg-emerald-600 hover:bg-emerald-700">
            New Scan
          </Button>
        </Link>
      </div>

      {error && (
        <Card className="border-red-500/50 bg-red-950/20 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </Card>
      )}

      {scans.length === 0 ? (
        <Card className="bg-neutral-900 border-neutral-800 border-dashed p-12 text-center">
          <h2 className="text-lg font-semibold mb-2">No scans yet</h2>
          <p className="text-neutral-400 text-sm mb-6">
            Paste a GitHub URL to run your first audit.
          </p>
          <Link href="/scan/new">
            <Button className="bg-emerald-600 hover:bg-emerald-700">
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
              className="bg-neutral-900 border-neutral-800 p-4 hover:border-neutral-700 transition-colors"
            >
              <div className="flex items-center justify-between gap-3">
                <Link
                  href={scan.status === "completed" ? `/scan/${scan.id}/report` : `/scan/${scan.id}`}
                  className="flex-1 min-w-0"
                >
                  <div className="cursor-pointer">
                    <p className="font-medium truncate">{scan.repo_name || scan.repo_url}</p>
                    <p className="text-xs text-neutral-500 mt-1">
                      {new Date(scan.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </Link>

                <div className="flex items-center gap-2 shrink-0">
                  {scan.status === "completed" && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-8 text-neutral-400 hover:text-neutral-200"
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
                        className="size-8 text-neutral-500 hover:text-red-400"
                        disabled={deletingId === scan.id}
                      >
                        {deletingId === scan.id ? (
                          <Loader2 className="size-4 animate-spin" />
                        ) : (
                          <Trash2 className="size-4" />
                        )}
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent className="bg-neutral-900 border-neutral-800">
                      <AlertDialogHeader>
                        <AlertDialogTitle>Delete this scan?</AlertDialogTitle>
                        <AlertDialogDescription className="text-neutral-400">
                          This will permanently delete the scan for{" "}
                          <span className="font-medium text-neutral-300">
                            {scan.repo_name || scan.repo_url}
                          </span>
                          . This action cannot be undone.
                        </AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel className="border-neutral-700">
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
