"use client";

import { motion } from "motion/react";
import {
  IconScan,
  IconStatus,
  IconConfig,
  IconHealth,
} from "@/components/landing/landing-icons";

/**
 * Shows the 4 MCP tools the wizard registers into Claude Code.
 * Each card has a hover glow + subtle float on enter.
 */

const TOOLS = [
  {
    name: "forge_scan",
    desc: "Run the full discovery pipeline on a repo path. Returns findings + Production Readiness Score.",
    icon: IconScan,
  },
  {
    name: "forge_status",
    desc: "Live progress of an in-flight scan: phase, active agents, cost, and time.",
    icon: IconStatus,
  },
  {
    name: "forge_config",
    desc: "Active vibe2prod URL, forgeignore sharing consent, installed version.",
    icon: IconConfig,
  },
  {
    name: "forge_health",
    desc: "Health check. Reports whether OPENROUTER_API_KEY is set and the MCP server is reachable.",
    icon: IconHealth,
  },
];

const card = {
  hidden: { opacity: 0, y: 16 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: 0.1 + i * 0.12,
      duration: 0.5,
      ease: [0.25, 0.46, 0.45, 0.94] as const,
    },
  }),
};

export function MCPToolsStrip() {
  return (
    <div>
      <div className="text-center mb-6">
        <p className="text-xs uppercase tracking-[0.25em] text-forge-emerald font-mono mb-2">
          MCP server registers
        </p>
        <h3 className="text-2xl sm:text-3xl font-bold font-[family-name:var(--font-heading)]">
          Four tools, straight into <span className="text-[#D97757]">Claude Code</span>
        </h3>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {TOOLS.map((t, i) => (
          <motion.div
            key={t.name}
            custom={i}
            variants={card}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-80px" }}
            whileHover={{ y: -4, transition: { duration: 0.2 } }}
            className="group relative rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 overflow-hidden transition-colors hover:border-forge-emerald/30"
          >
            {/* Hover glow */}
            <div className="absolute inset-0 bg-gradient-to-br from-forge-emerald/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />

            <div className="relative">
              <div className="inline-flex items-center justify-center size-9 rounded-lg bg-forge-emerald/10 border border-forge-emerald/20 text-forge-emerald mb-3">
                <t.icon className="size-4" />
              </div>
              <div className="font-mono text-sm text-[#E8ECF4] mb-1.5">
                {t.name}
              </div>
              <p className="text-xs text-[#8692A8] leading-relaxed">
                {t.desc}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
