"use client";

import Link from "next/link";
import { RefreshCw, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { scoreColorClass } from "@/app/(app)/dashboard/_components/dashboard-utils";
import { ScanRow, type ScanSummary } from "./scan-row";
import type { ProjectSummary } from "@/lib/api/types";

interface ProjectsSectionProps {
  projects: ProjectSummary[];
  scans: ScanSummary[];
  projectScanMap: Map<string, ScanSummary[]>;
  downloadingId: string | null;
  deletingId: string | null;
  copyingId: string | null;
  copiedId: string | null;
  onDownload: (scan: ScanSummary) => void;
  onCopy: (scan: ScanSummary) => void;
  onDelete: (scanId: string) => void;
}

export function ProjectsSection({
  projects,
  scans,
  projectScanMap,
  downloadingId,
  deletingId,
  copyingId,
  copiedId,
  onDownload,
  onCopy,
  onDelete,
}: ProjectsSectionProps) {
  const projectIds = new Set(projects.map((p) => p.id));
  const ungrouped = scans.filter((s) => !s.project_id || !projectIds.has(s.project_id));

  return (
    <div className="space-y-4" data-tour="scan-list">
      <h2 className="text-lg font-semibold">Projects</h2>
      {projects.map((project) => {
        const allProjectScans = projectScanMap.get(project.id) || [];
        const projectScans = allProjectScans.slice(0, 3);
        // Prefer the live count from the returned scans list; fall back to the
        // persisted project.scan_count if the page hasn't loaded any scans yet.
        const projectScanCount = allProjectScans.length || project.scan_count || 0;
        const displayName = project.repo_name || project.repo_url;
        const repoUrlEncoded = encodeURIComponent(project.repo_url);

        return (
          <Card key={project.id} className="forge-glass-card p-0 overflow-hidden">
            <div className="flex items-center justify-between gap-3 p-4 border-b border-white/[0.06]">
              <Link href={`/project/${project.id}`} className="flex-1 min-w-0 group">
                <div className="flex items-center gap-2">
                  <h3 className="font-semibold text-[#E8ECF4] truncate group-hover:text-forge-emerald transition-colors">
                    {displayName}
                  </h3>
                  <ChevronRight className="size-4 text-[#4E586E] shrink-0 group-hover:text-forge-emerald transition-colors" />
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-[#8692A8]">
                  <span>{projectScanCount} scan{projectScanCount !== 1 ? "s" : ""}</span>
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
                    onDownload={onDownload}
                    onCopy={onCopy}
                    onDelete={onDelete}
                  />
                ))}
              </div>
            )}
          </Card>
        );
      })}

      {/* Ungrouped scans (no project_id) */}
      {ungrouped.length > 0 && (
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
                  onDownload={onDownload}
                  onCopy={onCopy}
                  onDelete={onDelete}
                />
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
