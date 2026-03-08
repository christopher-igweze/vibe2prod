import { TrendingUp, TrendingDown, Minus, Clock, BarChart3 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { type DashboardMetrics, scoreColorClass, relativeTime } from "./dashboard-utils";

function TrendRow({ label, score, delta }: { label: string; score: number | null; delta: number | null }) {
  if (score === null) return null;

  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-sm text-[#8692A8]">{label}</span>
      <div className="flex items-center gap-2">
        <span className={`text-sm font-semibold ${scoreColorClass(score)}`}>{score}</span>
        {delta !== null && (
          <span className={`flex items-center gap-0.5 text-xs font-medium ${
            delta > 0 ? "text-forge-emerald" : delta < 0 ? "text-red-400" : "text-[#4E586E]"
          }`}>
            {delta > 0 ? <TrendingUp className="size-3" /> : delta < 0 ? <TrendingDown className="size-3" /> : <Minus className="size-3" />}
            {delta > 0 ? "+" : ""}{delta}
          </span>
        )}
      </div>
    </div>
  );
}

interface DashboardInsightsProps {
  metrics: DashboardMetrics;
}

export function DashboardInsights({ metrics }: DashboardInsightsProps) {
  const hasScores = metrics.latestScores !== null;
  const hasTrends = Object.values(metrics.scoreDeltas).some((d) => d !== null);

  return (
    <Card className="p-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Left: Score Trends */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="size-4 text-[#4E586E]" />
            <h3 className="text-xs font-semibold text-[#8692A8] uppercase tracking-wider">
              {hasTrends ? "Score Trends" : "Latest Scores"}
            </h3>
          </div>
          {hasScores ? (
            <div className="divide-y divide-white/[0.04]">
              <TrendRow label="Health" score={metrics.latestScores!.health} delta={metrics.scoreDeltas.health} />
              <TrendRow label="Security" score={metrics.latestScores!.security} delta={metrics.scoreDeltas.security} />
              <TrendRow label="Reliability" score={metrics.latestScores!.reliability} delta={metrics.scoreDeltas.reliability} />
              <TrendRow label="Scalability" score={metrics.latestScores!.scalability} delta={metrics.scoreDeltas.scalability} />
            </div>
          ) : (
            <p className="text-sm text-[#4E586E]">Complete a scan to see scores</p>
          )}
          {hasScores && !hasTrends && (
            <p className="text-xs text-[#4E586E] mt-2">Scan again to see trends</p>
          )}
        </div>

        {/* Right: Quick Breakdown */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Clock className="size-4 text-[#4E586E]" />
            <h3 className="text-xs font-semibold text-[#8692A8] uppercase tracking-wider">Activity</h3>
          </div>
          <div className="space-y-3">
            {metrics.lastScanDate && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8692A8]">Last scan</span>
                <span className="text-sm text-[#E8ECF4]">{relativeTime(metrics.lastScanDate)}</span>
              </div>
            )}
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#8692A8]">Completed</span>
              <span className="text-sm text-forge-emerald font-medium">{metrics.completedCount}</span>
            </div>
            {metrics.failedCount > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8692A8]">Failed</span>
                <span className="text-sm text-red-400 font-medium">{metrics.failedCount}</span>
              </div>
            )}
            {(metrics.statusBreakdown["scanning"] ?? 0) > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8692A8]">In progress</span>
                <span className="text-sm text-yellow-400 font-medium">{metrics.statusBreakdown["scanning"]}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}
