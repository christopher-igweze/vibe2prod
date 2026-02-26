"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api/client";
import { QuotaLimits } from "@/lib/api/types";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ScanSummary {
  id: string;
  repo_url: string;
  repo_name: string;
  status: string;
  created_at: string;
  health_score: number | null;
  security_score: number | null;
  reliability_score: number | null;
  scalability_score: number | null;
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [quota, setQuota] = useState<QuotaLimits | null>(null);
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function load() {
      try {
        const token = (await getToken()) ?? undefined;
        const [q, s] = await Promise.all([
          apiFetch<QuotaLimits>("/api/limits", { token }).catch((e) => {
            if (e instanceof ApiError && e.status === 403) return null;
            throw e;
          }),
          apiFetch<ScanSummary[]>("/api/user/scans", { token }).catch(() => [] as ScanSummary[]),
        ]);
        if (q) setQuota(q);
        setScans(s);
      } catch {
        setError("Failed to load dashboard data");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [getToken]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 bg-neutral-800 rounded animate-pulse" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-neutral-800 rounded-lg animate-pulse" />
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

      {/* Quota cards */}
      {quota && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-neutral-900 border-neutral-800 p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Reports This Month
            </p>
            <p className="text-2xl font-bold mt-1">
              {quota.reports_generated}
              <span className="text-neutral-500 text-base font-normal">
                {" "}/ {quota.reports_limit}
              </span>
            </p>
            <div className="mt-2 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-emerald-500 rounded-full transition-all"
                style={{
                  width: `${Math.min(
                    100,
                    (quota.reports_generated / quota.reports_limit) * 100
                  )}%`,
                }}
              />
            </div>
          </Card>

          <Card className="bg-neutral-900 border-neutral-800 p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider">
              Projects
            </p>
            <p className="text-2xl font-bold mt-1">
              {quota.project_count}
              <span className="text-neutral-500 text-base font-normal">
                {" "}/ {quota.project_limit}
              </span>
            </p>
          </Card>

        </div>
      )}

      {/* Scan history / empty state */}
      {scans.length === 0 ? (
        <Card className="bg-neutral-900 border-neutral-800 border-dashed p-12 text-center">
          <div className="text-4xl mb-4">🔍</div>
          <h2 className="text-lg font-semibold mb-2">No scans yet</h2>
          <p className="text-neutral-400 text-sm mb-6">
            Paste a GitHub URL to run your first free audit.
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
            <Link
              key={scan.id}
              href={scan.status === "completed" ? `/scan/${scan.id}/report` : `/scan/${scan.id}`}
            >
              <Card className="bg-neutral-900 border-neutral-800 p-4 hover:border-neutral-700 transition-colors cursor-pointer">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{scan.repo_name || scan.repo_url}</p>
                    <p className="text-xs text-neutral-500 mt-1">
                      {new Date(scan.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    {scan.health_score != null && (
                      <span className="text-lg font-bold">
                        {scan.health_score}
                      </span>
                    )}
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
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
