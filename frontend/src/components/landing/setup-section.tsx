"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Copy, Terminal, Sparkles, Globe } from "lucide-react";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";

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
        <Terminal className="size-3.5 text-[#4E586E]" />
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
      title: "Install the CLI",
      description:
        "FORGE ships as the vibe2prod package on PyPI. One pip install brings down the CLI, the MCP server, and the bundled /forge and /forgeignore skills.",
      code: ["pip install vibe2prod"],
      label: "install",
    },
    {
      num: "02",
      title: "Run the interactive setup",
      description:
        "`vibe2prod setup` walks you through a TUI wizard: it prompts for your OpenRouter API key, detects Claude Code, registers the FORGE MCP server (forge_scan, forge_status, forge_config, forge_health), and copies the /forge + /forgeignore skills into ~/.claude/commands/ so they're ready to use in any project.",
      code: ["vibe2prod setup"],
      label: "interactive setup",
    },
    {
      num: "03",
      title: "Run /forge in any repo",
      description:
        "Open Claude Code inside your project. The /forge skill drives the full loop — scan with forge_scan, walk each finding, drop false positives into .forgeignore, apply fixes with Claude, then rescan until the report is green. /forgeignore is there to manage suppression entries long-term.",
      code: ["cd ~/my-supabase-app", "claude", "/forge"],
      label: "workflow",
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
          <p className="text-center text-[#8692A8] mb-16 max-w-2xl mx-auto">
            One pip install and an interactive wizard between you and an
            audited, auto-fixed repo. No uploads, no CI wiring, no dashboards
            to babysit.
          </p>
        </FadeInWhenVisible>

        <div className="space-y-10">
          {steps.map((step, i) => (
            <FadeInWhenVisible key={step.num} delay={i * 0.12}>
              <div className="grid md:grid-cols-[1fr_1.4fr] gap-6 md:gap-10 items-start">
                <div>
                  <div className="inline-flex items-center gap-2 text-forge-emerald text-xs font-mono uppercase tracking-wider mb-2">
                    <span>Step {step.num}</span>
                  </div>
                  <h3 className="text-2xl font-bold mb-3 font-[family-name:var(--font-heading)]">
                    {step.title}
                  </h3>
                  <p className="text-[#8692A8] leading-relaxed text-sm">
                    {step.description}
                  </p>
                </div>
                <CodeBlock lines={step.code} label={step.label} />
              </div>
            </FadeInWhenVisible>
          ))}
        </div>

        {/* Headless alternative */}
        <FadeInWhenVisible delay={0.4}>
          <div className="mt-16 rounded-xl border border-white/[0.06] bg-white/[0.02] p-6 sm:p-8">
            <div className="flex items-start gap-4 flex-col md:flex-row md:items-center md:justify-between mb-4">
              <div>
                <h3 className="text-lg font-bold font-[family-name:var(--font-heading)] mb-1">
                  CI / scripted install?
                </h3>
                <p className="text-sm text-[#8692A8]">
                  The headless mode skips the TUI and takes your key on the
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
        <FadeInWhenVisible delay={0.5}>
          <div className="mt-10 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 sm:p-10 text-center">
            <div className="inline-flex items-center justify-center size-12 rounded-xl bg-forge-emerald/10 text-forge-emerald mb-4">
              <Globe className="size-6" />
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
                <Sparkles className="size-4" /> Try the web UI
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
