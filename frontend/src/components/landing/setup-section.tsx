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
        "One pip install. FORGE ships as a Python package with the MCP server, the /forge skill, and a standalone CLI baked in.",
      code: ["pip install forge-engine"],
      label: "install",
    },
    {
      num: "02",
      title: "Register the MCP server in Claude Code",
      description:
        "Adds four tools — forge_scan, forge_status, forge_config, forge_health — to every Claude Code session. Bring your own OpenRouter key and the LLM cost bills directly to you.",
      code: [
        "claude mcp add forge \\",
        "  -e OPENROUTER_API_KEY=sk-or-… \\",
        "  -- python -m forge.mcp_server",
      ],
      label: "mcp setup",
    },
    {
      num: "03",
      title: "Run /forge in your repo",
      description:
        "Inside Claude Code, from your project directory, invoke the slash skill. It runs forge_scan, walks you through the findings, lets you drop false positives into .forgeignore, fixes the real issues, then reruns the scan until clean.",
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
            Three commands between you and an audited, auto-fixed repo. No
            uploads, no CI wiring, no dashboards to babysit.
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

        {/* Alt path — web UI */}
        <FadeInWhenVisible delay={0.4}>
          <div className="mt-20 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 sm:p-10 text-center">
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
