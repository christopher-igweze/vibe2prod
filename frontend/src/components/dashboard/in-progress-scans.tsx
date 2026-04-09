"use client";

import Link from "next/link";
import { Loader2 } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ScanSummary } from "./scan-row";

interface InProgressScansProps {
  scans: ScanSummary[];
}

/**
 * Surfaces any scans currently in pending/scanning status at the top of the
 * dashboard so the user can click straight through to the live progress view.
 */
export function InProgressScans({ scans }: InProgressScansProps) {
  const inFlight = scans.filter(
    (s) => s.status === "pending" || s.status === "scanning" || s.status === "running",
  );

  if (inFlight.length === 0) return null;

  return (
    <Card className="border-forge-emerald/30 bg-forge-emerald/5 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Loader2 className="size-4 animate-spin text-forge-emerald" />
        <h3 className="text-sm font-semibold text-forge-emerald">
          {inFlight.length === 1 ? "Scan in progress" : `${inFlight.length} scans in progress`}
        </h3>
      </div>
      <div className="space-y-2">
        {inFlight.map((scan) => {
          const label =
            scan.repo_name ||
            scan.repo_url ||
            new Date(scan.created_at).toLocaleString();
          return (
            <Link
              key={scan.id}
              href={`/scan/${scan.id}`}
              className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 text-sm text-[#E8ECF4] hover:bg-white/[0.04] transition-colors"
            >
              <span className="truncate">{label}</span>
              <Badge variant="secondary" className="text-[10px] capitalize">
                {scan.status}
              </Badge>
            </Link>
          );
        })}
      </div>
    </Card>
  );
}
