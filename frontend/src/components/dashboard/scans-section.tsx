"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScanRow, type ScanSummary } from "./scan-row";

interface ScansSectionProps {
  scans: ScanSummary[];
  downloadingId: string | null;
  deletingId: string | null;
  copyingId: string | null;
  copiedId: string | null;
  onDownload: (scan: ScanSummary) => void;
  onCopy: (scan: ScanSummary) => void;
  onDelete: (scanId: string) => void;
}

export function EmptyScans() {
  return (
    <Card className="border-dashed p-12 text-center" data-tour="scan-list">
      <h2 className="text-lg font-semibold mb-2">No scans yet</h2>
      <p className="text-[#8692A8] text-sm mb-6">
        Paste a GitHub URL to run your first audit.
      </p>
      <Link href="/scan/new">
        <Button className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
          Start Your First Scan
        </Button>
      </Link>
    </Card>
  );
}

export function FlatScansList({
  scans,
  downloadingId,
  deletingId,
  copyingId,
  copiedId,
  onDownload,
  onCopy,
  onDelete,
}: ScansSectionProps) {
  return (
    <div className="space-y-3" data-tour="scan-list">
      <h2 className="text-lg font-semibold">Recent Scans</h2>
      {scans.map((scan) => (
        <Card
          key={scan.id}
          className="forge-glass-hover p-0 transition-colors"
        >
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
  );
}
