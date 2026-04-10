"use client";

import { motion } from "motion/react";
import { Wrench, User } from "lucide-react";
import { IconPrompt, IconClaude } from "@/components/landing/landing-icons";

/**
 * Faux Claude Code chat window showing the /forge slash skill in action.
 * The point is to make it concrete that FORGE lives inside Claude Code —
 * user types /forge, the MCP tools get invoked, findings stream in, and
 * Claude offers to fix.
 */

const bubbleIn = {
  hidden: { opacity: 0, y: 12 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: 0.3 + i * 0.35,
      duration: 0.5,
      ease: [0.25, 0.46, 0.45, 0.94] as const,
    },
  }),
};

function Bubble({
  i,
  children,
  side,
}: {
  i: number;
  children: React.ReactNode;
  side: "user" | "assistant";
}) {
  return (
    <motion.div
      custom={i}
      variants={bubbleIn}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-80px" }}
      className={`flex gap-3 ${side === "user" ? "justify-end" : "justify-start"}`}
    >
      {side === "assistant" && (
        <div className="shrink-0 mt-1 size-7 rounded-full bg-forge-emerald/10 border border-forge-emerald/20 flex items-center justify-center">
          <IconPrompt className="size-3.5 text-forge-emerald" />
        </div>
      )}
      <div
        className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
          side === "user"
            ? "bg-forge-emerald/10 border border-forge-emerald/20 text-[#E8ECF4]"
            : "bg-white/[0.04] border border-white/[0.08] text-[#E8ECF4]"
        }`}
      >
        {children}
      </div>
      {side === "user" && (
        <div className="shrink-0 mt-1 size-7 rounded-full bg-white/[0.06] border border-white/[0.08] flex items-center justify-center">
          <User className="size-3.5 text-[#8692A8]" />
        </div>
      )}
    </motion.div>
  );
}

function ToolCall({
  name,
  children,
  i,
}: {
  name: string;
  children: React.ReactNode;
  i: number;
}) {
  return (
    <motion.div
      custom={i}
      variants={bubbleIn}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-80px" }}
      className="rounded-lg border border-forge-emerald/20 bg-forge-emerald/[0.03] px-3 py-2 my-2"
    >
      <div className="flex items-center gap-1.5 text-[11px] text-forge-emerald font-mono mb-1">
        <Wrench className="size-3" />
        <span>{name}</span>
      </div>
      <div className="font-mono text-[11.5px] text-[#8692A8] leading-relaxed whitespace-pre-wrap">
        {children}
      </div>
    </motion.div>
  );
}

export function ClaudeCodeDemo() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-[#0a0e17]/95 overflow-hidden shadow-[0_0_60px_-20px_rgba(52,211,153,0.2)]">
      {/* Window chrome — Claude Code */}
      <div className="flex items-center gap-1.5 px-4 py-2 border-b border-white/[0.06]">
        <span className="size-2.5 rounded-full bg-[#ff5f56]/70" />
        <span className="size-2.5 rounded-full bg-[#ffbd2e]/70" />
        <span className="size-2.5 rounded-full bg-[#27c93f]/70" />
        <div className="mx-auto flex items-center gap-1.5 text-[11px] text-[#4E586E] font-mono">
          <IconClaude className="size-3 text-[#D97757]" />
          <span><span className="text-[#D97757]">Claude Code</span> · my-supabase-app</span>
        </div>
      </div>

      {/* Chat body */}
      <div className="px-5 py-6 sm:px-7 sm:py-8 space-y-4 min-h-[460px]">
        <Bubble i={0} side="user">
          <span className="font-mono text-forge-emerald">/forge</span>
        </Bubble>

        <Bubble i={1} side="assistant">
          I&rsquo;ll run the FORGE audit flow on this repo: scan, triage,
          fix, and rescan until clean. Starting with{" "}
          <code className="text-forge-emerald">forge_scan</code>.
        </Bubble>

        <ToolCall i={2} name="forge_scan(path='.')">
{`Scanning /Users/you/my-supabase-app…
  ✓ 16 Opengrep rules executed (0.8s)
  ✓ Codebase Analyst mapped 142 files
  ✓ Security Auditor reviewed 18 findings

Critical: 2   High: 4   Medium: 7   Low: 5
Readiness Score: 62 / 100`}
        </ToolCall>

        <Bubble i={3} side="assistant">
          One <span className="text-red-400 font-semibold">critical</span>{" "}
          finding stands out. A client can directly write to the{" "}
          <code className="text-forge-emerald">profiles.role</code> column
          from the browser:
          <div className="mt-2 rounded-md bg-[#0B0F19]/80 border border-white/[0.06] px-3 py-2 font-mono text-[11.5px] text-[#E8ECF4]">
            src/api/profile.ts:47
            <br />
            <span className="text-[#4E586E]">
              → flagged by Opengrep + Security Auditor
            </span>
            <br />
            <span className="text-[#4E586E]">
              → classic AI-generated Supabase mistake
            </span>
          </div>
          Want me to patch it and add a server-side guard? <span className="text-forge-emerald">(Y/n)</span>
        </Bubble>
      </div>
    </div>
  );
}
