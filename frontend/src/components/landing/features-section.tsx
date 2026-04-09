"use client";

import { Terminal, Search, Wrench } from "lucide-react";
import {
  FadeInWhenVisible,
  TiltCard,
} from "@/components/landing/motion-primitives";

export function FeaturesSection() {
  const features = [
    {
      title: "Install",
      subtitle: "One command inside Claude Code.",
      description:
        "Pip install forge-engine, then `claude mcp add forge` to register the MCP server. You get four tools in any Claude Code session: forge_scan, forge_status, forge_config, and forge_health. No web UI required — your repo never leaves your machine.",
      icon: Terminal,
    },
    {
      title: "Scan",
      subtitle: "Opengrep + 2 targeted LLM agents.",
      description:
        "16 deterministic Opengrep rules run first (secrets, SQL injection, XSS, path traversal, SSRF, auth bypass, CORS, insecure crypto, N+1, silent exceptions, more) at zero LLM cost. Then a Codebase Analyst (Minimax M2.5) maps your architecture and a Security Auditor (Claude Haiku 4.5) reasons over findings for context and severity.",
      icon: Search,
    },
    {
      title: "Fix with /forge",
      subtitle: "The slash skill closes the loop.",
      description:
        "Run `/forge` in Claude Code and the skill walks the full cycle: scan, triage findings, update .forgeignore for false positives with structured v2 entries, fix real issues with Claude, then rescan to verify. Autonomous, auditable, and you stay in control of the diff.",
      icon: Wrench,
    },
  ];

  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)]">
            One MCP install. One slash command. Shipped.
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-16 max-w-2xl mx-auto">
            CodeQL and Snyk hand you a report. FORGE runs inside Claude Code,
            applies the fixes, and reruns the scan until it&rsquo;s clean.
          </p>
        </FadeInWhenVisible>

        <div className="space-y-16 md:space-y-24">
          {features.map((feature, i) => (
            <FadeInWhenVisible
              key={feature.title}
              delay={i * 0.15}
              className={`flex flex-col ${
                i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              } items-center gap-8 md:gap-16`}
            >
              {/* Icon block with 3D tilt */}
              <div
                className="flex-1 flex items-center justify-center"
                style={{ perspective: "800px" }}
              >
                <TiltCard className="relative w-52 h-52 sm:w-64 sm:h-64 rounded-3xl forge-glass-card forge-gradient-border flex items-center justify-center">
                  <feature.icon
                    className="size-16 sm:size-20 text-forge-emerald"
                    strokeWidth={1.5}
                  />
                  {/* Floating number badge — pops out in 3D */}
                  <div
                    className="absolute -top-3 -left-3 w-10 h-10 rounded-full bg-forge-emerald text-[#0B0F19] flex items-center justify-center font-bold text-lg font-[family-name:var(--font-heading)]"
                    style={{ transform: "translateZ(30px)" }}
                  >
                    {i + 1}
                  </div>
                  {/* Inner glow on hover */}
                  <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-forge-emerald/10 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-500" />
                </TiltCard>
              </div>

              {/* Text block */}
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-3xl font-bold mb-2 font-[family-name:var(--font-heading)]">
                  {feature.title}
                </h3>
                <p className="text-forge-emerald text-sm font-medium mb-4">
                  {feature.subtitle}
                </p>
                <p className="text-[#8692A8] leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </FadeInWhenVisible>
          ))}
        </div>
      </div>
    </section>
  );
}
