"use client";

import { Card } from "@/components/ui/card";
import type { ScanSummary } from "@/components/dashboard/scan-row";

interface UsageStatsPanelProps {
  scans: ScanSummary[];
  isByok: boolean;
}

function formatUsd(amount: number): string {
  return `$${amount.toFixed(2)}`;
}

function isSameCalendarMonth(d: Date, ref: Date): boolean {
  return d.getFullYear() === ref.getFullYear() && d.getMonth() === ref.getMonth();
}

export function UsageStatsPanel({ scans, isByok }: UsageStatsPanelProps) {
  const now = new Date();

  // Only consider scans with a non-null cost_usd for dollar math.
  const costed = scans.filter(
    (s) => typeof s.cost_usd === "number" && !Number.isNaN(s.cost_usd),
  ) as (ScanSummary & { cost_usd: number })[];

  const allTime = costed.reduce((sum, s) => sum + s.cost_usd, 0);
  const thisMonthScans = costed.filter((s) => {
    const created = new Date(s.created_at);
    return isSameCalendarMonth(created, now);
  });
  const thisMonth = thisMonthScans.reduce((sum, s) => sum + s.cost_usd, 0);
  const avgPerScan = costed.length > 0 ? allTime / costed.length : 0;

  // Recent 5 (by created_at desc — scans are already newest-first from API,
  // but we sort defensively).
  const recent = [...scans]
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  // BYOK branch: show scan counts instead of dollar totals.
  if (isByok) {
    const totalScans = scans.length;
    const monthScans = scans.filter((s) =>
      isSameCalendarMonth(new Date(s.created_at), now),
    ).length;

    if (totalScans === 0) return null;

    return (
      <Card className="forge-glass-card p-6 space-y-5">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-[#E8ECF4] font-[family-name:var(--font-heading)]">
              Usage Stats
            </h2>
            <p className="text-xs text-[#8692A8] mt-0.5">
              Billed directly via your OpenRouter key
            </p>
          </div>
          <span className="text-[10px] bg-forge-emerald/20 text-forge-emerald px-2 py-0.5 rounded-full font-semibold">
            BYOK
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs text-[#8692A8] uppercase tracking-wide">This Month</p>
            <p className="text-2xl font-semibold text-[#E8ECF4] mt-1">{monthScans}</p>
            <p className="text-xs text-[#4E586E]">scans</p>
          </div>
          <div>
            <p className="text-xs text-[#8692A8] uppercase tracking-wide">All Time</p>
            <p className="text-2xl font-semibold text-[#E8ECF4] mt-1">{totalScans}</p>
            <p className="text-xs text-[#4E586E]">scans</p>
          </div>
        </div>
      </Card>
    );
  }

  // Non-BYOK: if we have nothing to show, render nothing.
  if (costed.length === 0 && allTime === 0) return null;

  return (
    <Card className="forge-glass-card p-6 space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-[#E8ECF4] font-[family-name:var(--font-heading)]">
          Usage Stats
        </h2>
        <p className="text-xs text-[#8692A8] mt-0.5">
          Your scan spend across Vibe2Prod
        </p>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div>
          <p className="text-xs text-[#8692A8] uppercase tracking-wide">This Month</p>
          <p className="text-2xl font-semibold text-forge-emerald mt-1">{formatUsd(thisMonth)}</p>
          <p className="text-xs text-[#4E586E]">{thisMonthScans.length} scans</p>
        </div>
        <div>
          <p className="text-xs text-[#8692A8] uppercase tracking-wide">All Time</p>
          <p className="text-2xl font-semibold text-[#E8ECF4] mt-1">{formatUsd(allTime)}</p>
          <p className="text-xs text-[#4E586E]">{costed.length} scans</p>
        </div>
        <div>
          <p className="text-xs text-[#8692A8] uppercase tracking-wide">Avg / Scan</p>
          <p className="text-2xl font-semibold text-[#E8ECF4] mt-1">{formatUsd(avgPerScan)}</p>
          <p className="text-xs text-[#4E586E]">per scan</p>
        </div>
      </div>

      {recent.length > 0 && (
        <div className="pt-2 border-t border-white/[0.06]">
          <p className="text-xs text-[#8692A8] uppercase tracking-wide mb-2">Recent Scans</p>
          <div className="space-y-1">
            {recent.map((scan) => (
              <div
                key={scan.id}
                className="flex items-center justify-between text-sm py-1.5 px-2 rounded hover:bg-white/[0.02]"
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <span className="text-[#8692A8] text-xs w-20 shrink-0">
                    {new Date(scan.created_at).toLocaleDateString()}
                  </span>
                  <span className="text-[#E8ECF4] truncate">
                    {scan.repo_name || scan.repo_url || "—"}
                  </span>
                  {scan.scan_tier && (
                    <span className="text-[10px] text-[#4E586E] uppercase shrink-0">
                      {scan.scan_tier}
                    </span>
                  )}
                </div>
                <span className="text-[#E8ECF4] font-mono text-xs shrink-0 ml-2">
                  {scan.cost_usd != null ? formatUsd(scan.cost_usd) : "—"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}
