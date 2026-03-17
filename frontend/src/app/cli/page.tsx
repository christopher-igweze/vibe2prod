"use client";

import { Lock, Zap, DollarSign } from "lucide-react";
import { CLINav, CLIHero } from "@/components/cli/cli-hero";
import { StepCard, FeatureCard } from "@/components/cli/terminal-primitives";
import { TerminalDemo } from "@/components/cli/terminal-demo";
import { QuickStart, DashboardConnect } from "@/components/cli/quick-start";
import { CLIFooter } from "@/components/cli/cli-footer";

export const dynamic = "force-dynamic";

export default function CLIPage() {
  return (
    <div className="min-h-screen bg-[#0a0e17] text-white overflow-hidden">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-emerald-500/[0.03] rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-0 w-[400px] h-[400px] bg-emerald-500/[0.02] rounded-full blur-[100px]" />
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage:
              "radial-gradient(circle, #34d399 1px, transparent 1px)",
            backgroundSize: "32px 32px",
          }}
        />
      </div>

      <CLINav />
      <CLIHero />

      {/* 3-Step Flow */}
      <section className="relative z-10 px-6 md:px-12 pb-20 max-w-4xl mx-auto">
        <div className="flex flex-col md:flex-row gap-4">
          <StepCard
            step={1}
            title="Install"
            command="pip3 install vibe2prod"
            description="One command. Installs the FORGE engine and MCP server."
            delay={0}
          />
          <StepCard
            step={2}
            title="Scan"
            command={`forge_scan(path=".")`}
            description="Discovers security, quality, and architecture issues in your codebase."
            delay={0.1}
          />
          <StepCard
            step={3}
            title="Fix"
            command="/forge"
            description="Claude reads the report and fixes findings using your own Edit tools. Locally."
            delay={0.2}
          />
        </div>
      </section>

      <TerminalDemo />

      {/* Features */}
      <section className="relative z-10 px-6 md:px-12 pb-20 max-w-4xl mx-auto">
        <div className="flex flex-col md:flex-row gap-4">
          <FeatureCard
            icon={Lock}
            title="Private"
            value="100%"
            description="Code never leaves your machine. Only anonymous telemetry metrics — no file paths, no code content."
            delay={0}
          />
          <FeatureCard
            icon={Zap}
            title="Scan Time"
            value="5-20 min"
            description="Full security, quality, and architecture audit. Depends on codebase size."
            delay={0.1}
          />
          <FeatureCard
            icon={DollarSign}
            title="Per Scan"
            value="$0.50-2"
            description="Your own OpenRouter API key. No subscription. Pay only for what you use."
            delay={0.2}
          />
        </div>
      </section>

      <QuickStart />
      <DashboardConnect />

      {/* Works With */}
      <section className="relative z-10 px-6 md:px-12 pb-20 max-w-4xl mx-auto text-center">
        <p className="text-zinc-600 text-xs uppercase tracking-widest mb-4">
          Works with any MCP-compatible tool
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          {["Claude Code", "Cursor", "Windsurf", "Cline", "Continue"].map(
            (tool) => (
              <span
                key={tool}
                className="px-4 py-2 rounded-lg bg-zinc-900/60 border border-zinc-800 text-zinc-400 text-sm hover:border-emerald-500/20 hover:text-zinc-200 transition-colors"
              >
                {tool}
              </span>
            )
          )}
        </div>
      </section>

      <CLIFooter />
    </div>
  );
}
