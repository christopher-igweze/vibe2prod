"use client";

export const dynamic = "force-dynamic";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useUserRole } from "@/hooks/use-user-role";
import { useTour } from "@/components/tour/tour-provider";
import { useDashboardState } from "@/hooks/use-dashboard-state";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { DashboardStats } from "./_components/dashboard-stats";
import { DashboardInsights } from "./_components/dashboard-insights";
import { ProjectsSection } from "@/components/dashboard/projects-section";
import { EmptyScans, FlatScansList } from "@/components/dashboard/scans-section";
import { InProgressScans } from "@/components/dashboard/in-progress-scans";
import { UsageStatsPanel } from "@/components/dashboard/usage-stats-panel";

export default function DashboardPage() {
  const { getToken } = useAuth();
  const { role, profile } = useUserRole();
  const { startTour } = useTour();

  const {
    scans,
    projects,
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
  } = useDashboardState(getToken);

  // Auto-trigger tour after onboarding
  useEffect(() => {
    if (!loading && profile?.onboarding_complete && profile?.tour_completed === false) {
      const timer = setTimeout(() => startTour("/dashboard"), 800);
      return () => clearTimeout(timer);
    }
  }, [loading, profile, startTour]);

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

      {profile?.has_openrouter_key ? (
        <div className="flex items-center gap-2 text-sm">
          <span className="text-[11px] bg-forge-emerald/20 text-forge-emerald px-2 py-0.5 rounded-full font-semibold">BYOK</span>
          <span className="text-[#8692A8]">
            Scans bill directly to your OpenRouter account.
            {role === "developer" && " Unlimited scans (Developer)."}
          </span>
        </div>
      ) : role === "developer" ? (
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

      <InProgressScans scans={scans} />

      {scans.length > 0 && (
        <div data-tour="stats-panel" className="space-y-4">
          <DashboardStats metrics={metrics} />
          <DashboardInsights metrics={metrics} />
        </div>
      )}

      {scans.length > 0 && (
        <UsageStatsPanel scans={scans} isByok={!!profile?.has_openrouter_key} />
      )}

      {scans.length === 0 ? (
        <EmptyScans />
      ) : projects.length > 0 ? (
        <ProjectsSection
          projects={projects}
          scans={scans}
          projectScanMap={projectScanMap}
          downloadingId={downloadingId}
          deletingId={deletingId}
          copyingId={copyingId}
          copiedId={copiedId}
          onDownload={handleDownload}
          onCopy={handleCopy}
          onDelete={handleDelete}
        />
      ) : (
        <FlatScansList
          scans={scans}
          downloadingId={downloadingId}
          deletingId={deletingId}
          copyingId={copyingId}
          copiedId={copiedId}
          onDownload={handleDownload}
          onCopy={handleCopy}
          onDelete={handleDelete}
        />
      )}
    </div>
  );
}
