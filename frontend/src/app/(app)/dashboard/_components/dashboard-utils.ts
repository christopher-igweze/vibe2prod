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

export interface DashboardMetrics {
  totalScans: number;
  completedCount: number;
  failedCount: number;
  avgHealth: number | null;
  avgSecurity: number | null;
  avgReliability: number | null;
  avgScalability: number | null;
  topRepo: { name: string; count: number } | null;
  latestScores: {
    health: number | null;
    security: number | null;
    reliability: number | null;
    scalability: number | null;
  } | null;
  scoreDeltas: {
    health: number | null;
    security: number | null;
    reliability: number | null;
    scalability: number | null;
  };
  lastScanDate: Date | null;
  statusBreakdown: Record<string, number>;
}

function avg(nums: number[]): number | null {
  if (nums.length === 0) return null;
  return Math.round(nums.reduce((a, b) => a + b, 0) / nums.length);
}

export function scoreColor(score: number): string {
  if (score >= 70) return "#34d399";
  if (score >= 40) return "#fbbf24";
  return "#ef4444";
}

export function scoreColorClass(score: number): string {
  if (score >= 70) return "text-forge-emerald";
  if (score >= 40) return "text-yellow-400";
  return "text-red-400";
}

export function scoreBgClass(score: number): string {
  if (score >= 70) return "bg-forge-emerald";
  if (score >= 40) return "bg-yellow-400";
  return "bg-red-400";
}

export function relativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 30) return `${diffDays}d ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

export function computeDashboardMetrics(scans: ScanSummary[]): DashboardMetrics {
  const completed = scans.filter((s) => s.status === "completed");
  const failed = scans.filter((s) => s.status === "failed");

  // Scores from completed scans (filter nulls)
  const healthScores = completed.map((s) => s.health_score).filter((v): v is number => v !== null);
  const securityScores = completed.map((s) => s.security_score).filter((v): v is number => v !== null);
  const reliabilityScores = completed.map((s) => s.reliability_score).filter((v): v is number => v !== null);
  const scalabilityScores = completed.map((s) => s.scalability_score).filter((v): v is number => v !== null);

  // Top repo by scan count
  const repoCounts: Record<string, number> = {};
  for (const s of scans) {
    const name = s.repo_name || s.repo_url;
    if (name) repoCounts[name] = (repoCounts[name] || 0) + 1;
  }
  const topRepoEntry = Object.entries(repoCounts).sort((a, b) => b[1] - a[1])[0];
  const topRepo = topRepoEntry ? { name: topRepoEntry[0], count: topRepoEntry[1] } : null;

  // Latest scores (first completed scan, already sorted desc by created_at)
  const latestCompleted = completed[0] ?? null;
  const latestScores = latestCompleted
    ? {
        health: latestCompleted.health_score,
        security: latestCompleted.security_score,
        reliability: latestCompleted.reliability_score,
        scalability: latestCompleted.scalability_score,
      }
    : null;

  // Score deltas: latest vs average of prior
  const prior = completed.slice(1);
  const priorHealth = prior.map((s) => s.health_score).filter((v): v is number => v !== null);
  const priorSecurity = prior.map((s) => s.security_score).filter((v): v is number => v !== null);
  const priorReliability = prior.map((s) => s.reliability_score).filter((v): v is number => v !== null);
  const priorScalability = prior.map((s) => s.scalability_score).filter((v): v is number => v !== null);

  function delta(latest: number | null, priorArr: number[]): number | null {
    if (latest === null || priorArr.length === 0) return null;
    const priorAvg = avg(priorArr);
    if (priorAvg === null) return null;
    return latest - priorAvg;
  }

  const scoreDeltas = {
    health: delta(latestScores?.health ?? null, priorHealth),
    security: delta(latestScores?.security ?? null, priorSecurity),
    reliability: delta(latestScores?.reliability ?? null, priorReliability),
    scalability: delta(latestScores?.scalability ?? null, priorScalability),
  };

  // Status breakdown
  const statusBreakdown: Record<string, number> = {};
  for (const s of scans) {
    statusBreakdown[s.status] = (statusBreakdown[s.status] || 0) + 1;
  }

  // Last scan date
  const lastScanDate = completed.length > 0 ? new Date(completed[0].created_at) : null;

  return {
    totalScans: scans.length,
    completedCount: completed.length,
    failedCount: failed.length,
    avgHealth: avg(healthScores),
    avgSecurity: avg(securityScores),
    avgReliability: avg(reliabilityScores),
    avgScalability: avg(scalabilityScores),
    topRepo,
    latestScores,
    scoreDeltas,
    lastScanDate,
    statusBreakdown,
  };
}
