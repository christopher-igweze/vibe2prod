"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Copy, ArrowRight } from "lucide-react";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";
import { SetupTuiPreview } from "@/components/landing/setup-tui-preview";
import { MCPToolsStrip } from "@/components/landing/mcp-tools-strip";
import { ClaudeCodeDemo } from "@/components/landing/claude-code-demo";
import { IconBrowser, IconPrompt } from "@/components/landing/landing-icons";

interface CodeBlockProps {
  lines: string[];
  label?: string;
}

function CodeBlock({ lines, label }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard?.writeText(lines.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };
  return (
    <div className="rounded-lg border border-white/[0.08] bg-[#0a0e17]/90 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-white/[0.06]">
        <IconPrompt className="size-3.5 text-[#4E586E]" />
        <span className="text-[11px] text-[#4E586E] font-mono">
          {label ?? "terminal"}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          aria-label="Copy command"
          className="ml-auto p-1 rounded text-[#4E586E] hover:text-forge-emerald hover:bg-white/[0.04] transition-colors"
        >
          {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
        </button>
      </div>
      <div className="px-5 py-4 font-mono text-[13px] leading-relaxed text-[#E8ECF4] overflow-x-auto">
        {lines.map((line) => (
          <div key={line} className="whitespace-pre">
            <span className="text-forge-emerald">$</span> {line}
          </div>
        ))}
      </div>
    </div>
  );
}

export function SetupSection() {
  const steps = [
    {
      num: "01",
      title: "Install",
      command: "pip install vibe2prod",
      desc: "Ships the CLI, MCP server, and bundled skills.",
    },
    {
      num: "02",
      title: "Run the wizard",
      command: "vibe2prod setup",
      desc: "Registers the MCP server + installs /forge & /forgeignore.",
    },
    {
      num: "03",
      title: "Use /forge",
      command: "claude → /forge",
      desc: "Audit, triage, fix, and rescan. All inside Claude Code.",
    },
  ];

  return (
    <section id="setup" className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-5xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-3 font-[family-name:var(--font-heading)]">
            Set up in 60 seconds
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-12 max-w-2xl mx-auto">
            One pip install, one interactive wizard. Point FORGE at Claude Code
            and it registers the MCP server, installs the{" "}
            <code className="text-forge-emerald">/forge</code> and{" "}
            <code className="text-forge-emerald">/forgeignore</code> slash
            skills, and you&rsquo;re scanning in a minute.
          </p>
        </FadeInWhenVisible>

        {/* Hero TUI preview */}
        <FadeInWhenVisible delay={0.15}>
          <SetupTuiPreview />
        </FadeInWhenVisible>

        {/* MCP tools strip — what the wizard just registered */}
        <div className="mt-16">
          <MCPToolsStrip />
        </div>

        {/* Claude Code /forge demo */}
        <div className="mt-16">
          <div className="text-center mb-6">
            <p className="text-xs uppercase tracking-[0.25em] text-forge-emerald font-mono mb-2">
              Then in Claude Code
            </p>
            <h3 className="text-2xl sm:text-3xl font-bold font-[family-name:var(--font-heading)]">
              <span className="text-forge-emerald font-mono">/forge</span> drives the loop
            </h3>
          </div>
          <FadeInWhenVisible>
            <ClaudeCodeDemo />
          </FadeInWhenVisible>
        </div>

        {/* 3-step summary underneath */}
        <FadeInWhenVisible delay={0.25}>
          <div className="mt-10 grid grid-cols-1 md:grid-cols-3 gap-4">
            {steps.map((step) => (
              <div
                key={step.num}
                className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-5"
              >
                <div className="text-[11px] font-mono uppercase tracking-wider text-forge-emerald mb-1">
                  Step {step.num}
                </div>
                <h3 className="text-lg font-bold mb-2 font-[family-name:var(--font-heading)]">
                  {step.title}
                </h3>
                <div className="rounded-md border border-white/[0.06] bg-[#0a0e17]/80 px-3 py-2 font-mono text-[12px] text-[#E8ECF4] mb-3 overflow-x-auto">
                  <span className="text-forge-emerald">$</span> {step.command}
                </div>
                <p className="text-xs text-[#8692A8] leading-relaxed">
                  {step.desc}
                </p>
              </div>
            ))}
          </div>
        </FadeInWhenVisible>

        {/* Headless alternative */}
        <FadeInWhenVisible delay={0.35}>
          <div className="mt-10 rounded-xl border border-white/[0.06] bg-white/[0.02] p-6 sm:p-8">
            <div className="flex items-start gap-4 flex-col md:flex-row md:items-center md:justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold font-[family-name:var(--font-heading)] mb-1">
                  CI / scripted install?
                </h3>
                <p className="text-sm text-[#8692A8]">
                  Headless mode skips the TUI and takes your key on the
                  command line. Useful for Docker images, dotfiles, and AI
                  agents running the setup themselves.
                </p>
              </div>
            </div>
            <CodeBlock
              lines={["vibe2prod setup --no-interactive --api-key sk-or-…"]}
              label="headless"
            />
          </div>
        </FadeInWhenVisible>

        {/* Alt path — web UI */}
        <FadeInWhenVisible delay={0.45}>
          <div className="mt-10 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 sm:p-10 text-center">
            <div className="inline-flex items-center justify-center size-12 rounded-xl bg-forge-emerald/10 border border-forge-emerald/20 text-forge-emerald mb-4">
              <IconBrowser className="size-6" />
            </div>
            <h3 className="text-2xl font-bold mb-2 font-[family-name:var(--font-heading)]">
              Not using Claude Code? Use the web UI.
            </h3>
            <p className="text-[#8692A8] max-w-xl mx-auto mb-6 text-sm leading-relaxed">
              Same FORGE engine, no install required. Sign in, paste a GitHub
              URL, and the scan runs in an ephemeral sandbox. $15 signup
              credit, pay-per-scan after.
            </p>
            <div className="flex items-center justify-center gap-3 flex-wrap">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 rounded-lg bg-forge-emerald px-5 py-2.5 text-sm font-semibold text-[#0B0F19] hover:bg-forge-emerald-light transition-colors"
              >
                <ArrowRight className="size-4" /> Try the web UI
              </Link>
              <Link
                href="/pricing"
                className="inline-flex items-center gap-2 rounded-lg border border-white/[0.08] px-5 py-2.5 text-sm font-semibold text-[#E8ECF4] hover:border-forge-emerald/40 hover:text-forge-emerald transition-colors"
              >
                See pricing
              </Link>
            </div>
          </div>
        </FadeInWhenVisible>
      </div>
    </section>
  );
}
