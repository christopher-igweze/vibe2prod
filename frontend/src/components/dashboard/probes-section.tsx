"use client";

import Link from "next/link";
import { Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { scoreColorClass } from "@/app/(app)/dashboard/_components/dashboard-utils";
import type { ProbeSummary } from "@/lib/api/types";

interface ProbesSectionProps {
  probes: ProbeSummary[];
}

export function ProbesSection({ probes }: ProbesSectionProps) {
  if (probes.length === 0) {
    return (
      <div className="space-y-3">
        <h2 className="text-lg font-semibold">Live Probes</h2>
        <Card className="border-dashed p-8 text-center">
          <Shield className="size-6 text-[#4E586E] mx-auto mb-2" />
          <p className="text-sm text-[#8692A8] mb-4">
            No probes yet. Test your deployed app for security vulnerabilities.
          </p>
          <Link href="/probe/new">
            <Button size="sm" className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]">
              Start Your First Probe
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Recent Probes</h2>
        <Link href="/probe/new">
          <Button size="sm" variant="ghost" className="text-[#8692A8] hover:text-forge-emerald gap-1.5">
            <Shield className="size-3.5" /> New Probe
          </Button>
        </Link>
      </div>
      {probes.slice(0, 5).map((probe) => (
        <Link key={probe.id} href={`/probe/${probe.id}`}>
          <Card className="forge-glass-hover p-0 transition-colors">
            <div className="flex items-center justify-between gap-3 py-2 px-3 rounded-lg hover:bg-white/[0.02] transition-colors">
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[#E8ECF4] truncate">{probe.target_url}</p>
                <div className="flex items-center gap-3 mt-0.5 text-xs text-[#8692A8]">
                  <span>{new Date(probe.created_at).toLocaleDateString()}</span>
                  {probe.probe_score !== null && (
                    <span className={scoreColorClass(probe.probe_score)}>
                      Score: {probe.probe_score}
                    </span>
                  )}
                  {probe.total_findings > 0 && (
                    <span>{probe.total_findings} finding{probe.total_findings !== 1 ? "s" : ""}</span>
                  )}
                </div>
              </div>
              <Badge
                className="ml-1 text-[10px]"
                variant={
                  probe.status === "completed"
                    ? "default"
                    : probe.status === "failed"
                    ? "destructive"
                    : "secondary"
                }
              >
                {probe.status}
              </Badge>
            </div>
          </Card>
        </Link>
      ))}
    </div>
  );
}
