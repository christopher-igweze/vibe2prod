"use client";

import { motion } from "motion/react";
import { TerminalLine, CopyButton } from "./terminal-primitives";

export function TerminalDemo() {
  return (
    <section className="relative z-10 px-6 md:px-12 pb-20 max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.6 }}
        className="relative"
      >
        <div className="bg-[#0d1117] border border-zinc-800 rounded-xl overflow-hidden shadow-2xl shadow-black/40">
          {/* Title bar */}
          <div className="flex items-center gap-2 px-4 py-3 bg-zinc-900/80 border-b border-zinc-800">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
            </div>
            <span className="text-zinc-500 text-xs ml-2 font-mono">
              ~/my-project
            </span>
          </div>

          {/* Terminal content */}
          <div className="p-5 font-[family-name:var(--font-jetbrains-mono)] text-[13px] leading-[1.9] relative">
            <CopyButton text={`pip3 install vibe2prod\nclaude mcp add forge -e OPENROUTER_API_KEY=your-key -- forge-mcp`} />

            <TerminalLine text='pip3 install vibe2prod' delay={500} />
            <TerminalLine text="  Successfully installed vibe2prod-0.3.1" delay={1500} isOutput />

            <TerminalLine text='claude mcp add forge -e OPENROUTER_API_KEY=sk-or... -- forge-mcp' delay={2500} />
            <TerminalLine text="  Added MCP server: forge" delay={3500} isOutput />

            <div className="h-3" />
            <TerminalLine text='"Scan my codebase with forge"' delay={4500} color="text-white" />
            <TerminalLine text="  Scanning 184 files..." delay={5500} isOutput />
            <TerminalLine text="  Security: 8 issues (2 critical, 3 high)" delay={6200} isOutput />
            <TerminalLine text="  Quality: 12 issues" delay={6800} isOutput />
            <TerminalLine text="  Architecture: 5 issues" delay={7300} isOutput />
            <TerminalLine text="  \u2713 42 findings | Readiness: 58/100 | $1.20 | 8 min" delay={7800} color="text-emerald-400" isOutput />

            <div className="h-3" />
            <TerminalLine text="/forge" delay={9000} />
            <TerminalLine text="  Reading scan report... 42 findings" delay={10000} isOutput />
            <TerminalLine text="  Fixing [critical] SQL injection in auth.py..." delay={10800} isOutput />
            <TerminalLine text="  Fixing [high] Missing error handling in routes.py..." delay={11500} isOutput />
            <TerminalLine text="  Fixing [high] Hardcoded secrets in config.py..." delay={12200} isOutput />
            <TerminalLine text="  \u2713 38 fixed | Readiness: 94/100" delay={13000} color="text-emerald-400" isOutput />
          </div>
        </div>
      </motion.div>
    </section>
  );
}
