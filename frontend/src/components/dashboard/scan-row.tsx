"use client";

import Link from "next/link";
import { Download, Trash2, Loader2, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
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
import { scoreColorClass } from "@/app/(app)/dashboard/_components/dashboard-utils";

export interface ScanSummary {
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

interface ScanRowProps {
  scan: ScanSummary;
  downloadingId: string | null;
  deletingId: string | null;
  copyingId: string | null;
  copiedId: string | null;
  onDownload: (scan: ScanSummary) => void;
  onCopy: (scan: ScanSummary) => void;
  onDelete: (scanId: string) => void;
}

export function ScanRow({
  scan,
  downloadingId,
  deletingId,
  copyingId,
  copiedId,
  onDownload,
  onCopy,
  onDelete,
}: ScanRowProps) {
  return (
    <div className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg hover:bg-white/[0.02] transition-colors">
      <Link
        href={scan.status === "completed" ? `/scan/${scan.id}/report` : `/scan/${scan.id}`}
        className="flex-1 min-w-0"
      >
        <div className="cursor-pointer flex items-center gap-3">
          <div className="min-w-0">
            <p className="text-sm text-[#E8ECF4] truncate">
              {new Date(scan.created_at).toLocaleDateString()}
              {scan.scan_tier && <span className="text-[#4E586E] ml-2">{scan.scan_tier}</span>}
            </p>
            {scan.health_score !== null && (
              <p className="text-xs mt-0.5">
                <span className={scoreColorClass(scan.health_score)}>
                  Health: {scan.health_score}
                </span>
              </p>
            )}
          </div>
        </div>
      </Link>

      <div className="flex items-center gap-1 shrink-0">
        {scan.status === "completed" && (
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-[#8692A8] hover:text-forge-emerald"
            disabled={copyingId === scan.id}
            onClick={() => onCopy(scan)}
          >
            {copyingId === scan.id ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : copiedId === scan.id ? (
              <Check className="size-3.5 text-forge-emerald" />
            ) : (
              <Copy className="size-3.5" />
            )}
          </Button>
        )}

        {scan.status === "completed" && (
          <Button
            variant="ghost"
            size="icon"
            className="size-7 text-[#8692A8] hover:text-forge-emerald"
            disabled={downloadingId === scan.id}
            onClick={() => onDownload(scan)}
          >
            {downloadingId === scan.id ? (
              <Loader2 className="size-3.5 animate-spin" />
            ) : (
              <Download className="size-3.5" />
            )}
          </Button>
        )}

        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              variant="ghost"
              size="icon"
              className="size-7 text-[#4E586E] hover:text-red-400"
              disabled={deletingId === scan.id}
            >
              {deletingId === scan.id ? (
                <Loader2 className="size-3.5 animate-spin" />
              ) : (
                <Trash2 className="size-3.5" />
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
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={() => onDelete(scan.id)}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Delete
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        <Badge
          className="ml-1 text-[10px]"
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
  );
}
