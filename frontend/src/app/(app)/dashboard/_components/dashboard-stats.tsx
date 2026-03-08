import { Activity, Shield, Heart, GitFork } from "lucide-react";
import { type DashboardMetrics, scoreColorClass, scoreBgClass } from "./dashboard-utils";

function ScoreBar({ score }: { score: number }) {
  const bg = scoreBgClass(score);
  return (
    <div className="h-1.5 w-full bg-white/[0.06] rounded-full overflow-hidden mt-2">
      <div
        className={`h-full rounded-full transition-all duration-700 ${bg}`}
        style={{ width: `${Math.max(0, Math.min(100, score))}%` }}
      />
    </div>
  );
}

interface DashboardStatsProps {
  metrics: DashboardMetrics;
}

export function DashboardStats({ metrics }: DashboardStatsProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      {/* Total Scans */}
      <div className="forge-glass-card rounded-xl p-4 space-y-1">
        <div className="flex items-center gap-2">
          <Activity className="size-4 text-[#4E586E]" />
          <span className="text-xs text-[#8692A8] uppercase tracking-wider">Total Scans</span>
        </div>
        <p className="text-2xl font-bold font-[family-name:var(--font-heading)] text-forge-emerald">
          {metrics.totalScans}
        </p>
        <p className="text-xs text-[#4E586E]">
          {metrics.completedCount} completed{metrics.failedCount > 0 ? `, ${metrics.failedCount} failed` : ""}
        </p>
      </div>

      {/* Avg Health */}
      <div className="forge-glass-card rounded-xl p-4 space-y-1">
        <div className="flex items-center gap-2">
          <Heart className="size-4 text-[#4E586E]" />
          <span className="text-xs text-[#8692A8] uppercase tracking-wider">Health</span>
        </div>
        {metrics.avgHealth !== null ? (
          <>
            <p className={`text-2xl font-bold font-[family-name:var(--font-heading)] ${scoreColorClass(metrics.avgHealth)}`}>
              {metrics.avgHealth}
              <span className="text-sm text-[#4E586E] font-normal">/100</span>
            </p>
            <ScoreBar score={metrics.avgHealth} />
          </>
        ) : (
          <p className="text-2xl font-bold text-[#4E586E]">--</p>
        )}
      </div>

      {/* Avg Security */}
      <div className="forge-glass-card rounded-xl p-4 space-y-1">
        <div className="flex items-center gap-2">
          <Shield className="size-4 text-[#4E586E]" />
          <span className="text-xs text-[#8692A8] uppercase tracking-wider">Security</span>
        </div>
        {metrics.avgSecurity !== null ? (
          <>
            <p className={`text-2xl font-bold font-[family-name:var(--font-heading)] ${scoreColorClass(metrics.avgSecurity)}`}>
              {metrics.avgSecurity}
              <span className="text-sm text-[#4E586E] font-normal">/100</span>
            </p>
            <ScoreBar score={metrics.avgSecurity} />
          </>
        ) : (
          <p className="text-2xl font-bold text-[#4E586E]">--</p>
        )}
      </div>

      {/* Top Repo */}
      <div className="forge-glass-card rounded-xl p-4 space-y-1">
        <div className="flex items-center gap-2">
          <GitFork className="size-4 text-[#4E586E]" />
          <span className="text-xs text-[#8692A8] uppercase tracking-wider">Top Repo</span>
        </div>
        {metrics.topRepo ? (
          <>
            <p className="text-lg font-bold font-[family-name:var(--font-heading)] text-[#E8ECF4] truncate" title={metrics.topRepo.name}>
              {metrics.topRepo.name.split("/").pop()}
            </p>
            <p className="text-xs text-[#4E586E]">{metrics.topRepo.count} scan{metrics.topRepo.count !== 1 ? "s" : ""}</p>
          </>
        ) : (
          <p className="text-2xl font-bold text-[#4E586E]">--</p>
        )}
      </div>
    </div>
  );
}
