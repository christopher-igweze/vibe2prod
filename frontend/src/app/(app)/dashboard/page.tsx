"use client";

export const dynamic = "force-dynamic";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { apiFetch } from "@/lib/api/client";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface ScanSummary {
  id: string;
  repo_url: string;
  repo_name: string;
  status: string;
  created_at: string;
}

export default function DashboardPage() {
  const { getToken } = useAuth();
  const [scans, setScans] = useState<ScanSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
