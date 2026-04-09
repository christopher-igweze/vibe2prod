"use client";

import { Terminal } from "lucide-react";
import { motion } from "motion/react";

/**
 * Faux terminal rendering of the `vibe2prod setup` Rich TUI wizard.
 * Mirrors the output of forge-engine/forge/setup_wizard.py — blue intro
 * panel, stepped prompts, green ✓ checkmarks, and the green Configuration
 * summary. Blocks are staggered in on scroll to feel like a live wizard.
 */

const blockVariants = {
  hidden: { opacity: 0, y: 8 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.2 + i * 0.25, duration: 0.45, ease: [0.25, 0.46, 0.45, 0.94] as const },
  }),
};

function Block({ i, children }: { i: number; children: React.ReactNode }) {
  return (
    <motion.span
      custom={i}
      variants={blockVariants}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-100px" }}
      style={{ display: "block" }}
    >
      {children}
    </motion.span>
  );
}

export function SetupTuiPreview() {
  return (
    <div className="rounded-xl border border-white/[0.08] bg-[#0a0e17]/95 overflow-hidden shadow-[0_0_60px_-20px_rgba(52,211,153,0.25)]">
      {/* Window chrome */}
      <div className="flex items-center gap-1.5 px-4 py-2 border-b border-white/[0.06]">
        <span className="size-2.5 rounded-full bg-[#ff5f56]/70" />
        <span className="size-2.5 rounded-full bg-[#ffbd2e]/70" />
        <span className="size-2.5 rounded-full bg-[#27c93f]/70" />
        <div className="mx-auto flex items-center gap-1.5 text-[11px] text-[#4E586E] font-mono">
          <Terminal className="size-3" />
          <span>vibe2prod setup</span>
        </div>
      </div>

      {/* Terminal body */}
      <pre className="px-5 py-5 sm:px-7 sm:py-6 font-mono text-[11px] sm:text-[12.5px] leading-[1.55] text-[#E8ECF4] overflow-x-auto whitespace-pre">
        <Block i={0}>
          <span className="text-forge-emerald">$</span> vibe2prod setup
          {"\n\n"}
        </Block>

        {/* Blue intro panel */}
        <Block i={1}>
          <span className="text-blue-400">{`╭─ vibe2prod `}</span>
          <span className="text-blue-400">{`─`.repeat(42)}</span>
          <span className="text-blue-400">{`╮`}</span>{"\n"}
          <span className="text-blue-400">{"│"}</span>
          {`                                                    `}
          <span className="text-blue-400">{"│"}</span>{"\n"}
          <span className="text-blue-400">{"│"}</span>
          {`  `}
          <span className="text-blue-300 font-bold">FORGE Setup Wizard</span>
          {`                              `}
          <span className="text-blue-400">{"│"}</span>{"\n"}
          <span className="text-blue-400">{"│"}</span>
          {`                                                    `}
          <span className="text-blue-400">{"│"}</span>{"\n"}
          <span className="text-blue-400">{"│"}</span>
          {`  Configure FORGE for local code auditing.         `}
          <span className="text-blue-400">{"│"}</span>{"\n"}
          <span className="text-blue-400">{"│"}</span>
          {`  Your code never leaves your machine — only LLM    `}
          <span className="text-blue-400">{"│"}</span>{"\n"}
          <span className="text-blue-400">{"│"}</span>
          {`  API calls go to OpenRouter.                       `}
          <span className="text-blue-400">{"│"}</span>{"\n"}
          <span className="text-blue-400">{"│"}</span>
          {`                                                    `}
          <span className="text-blue-400">{"│"}</span>{"\n"}
          <span className="text-blue-400">{`╰`}</span>
          <span className="text-blue-400">{`─`.repeat(52)}</span>
          <span className="text-blue-400">{`╯`}</span>{"\n\n"}
        </Block>

        {/* Step 1 */}
        <Block i={2}>
          <span className="font-bold text-[#E8ECF4]">Step 1/6 — OpenRouter API Key</span>
          <span className="text-[#8692A8]"> (optional)</span>{"\n"}
          <span className="text-[#8692A8]">{`  Enter your OpenRouter API key (press Enter to skip)\n`}</span>
          <span className="text-[#8692A8]">{`  Get yours at: https://openrouter.ai/keys\n\n`}</span>
          {`  OpenRouter API key: `}
          <span className="text-[#4E586E]">{`••••••••••••••••••••`}</span>{"\n\n"}
        </Block>

        {/* Step 2 + 3 collapsed */}
        <Block i={3}>
          <span className="font-bold text-[#E8ECF4]">Step 2/6 — Vibe2Prod Dashboard</span>
          <span className="text-[#8692A8]"> (optional)</span>{"\n"}
          {`  Enable dashboard sync? `}
          <span className="text-[#4E586E]">[Y/n]:</span>
          <span className="text-forge-emerald"> y</span>{"\n\n"}

          <span className="font-bold text-[#E8ECF4]">Step 3/6 — Data Sharing</span>{"\n"}
          {`  Share anonymized suppression data? `}
          <span className="text-[#4E586E]">[Y/n]:</span>
          <span className="text-forge-emerald"> y</span>{"\n\n"}
        </Block>

        {/* Step 4 — the money shot */}
        <Block i={4}>
          <span className="font-bold text-[#E8ECF4]">Step 4/6 — Claude Code Integration</span>{"\n"}
          {`  `}<span className="text-forge-emerald">Claude Code detected!</span>{"\n"}
          {`  Register FORGE as MCP server + install skills? `}
          <span className="text-[#4E586E]">[Y/n]:</span>
          <span className="text-forge-emerald"> y</span>{"\n"}
          {`  Register for all projects (user) or just this one? `}
          <span className="text-forge-emerald">user</span>{"\n"}
          {`  `}<span className="text-[#4E586E]">⠋ Registering MCP server...</span>{"\n"}
          {`  `}<span className="text-forge-emerald">✓</span>{` MCP server registered (user scope)\n`}
          {`  `}<span className="text-forge-emerald">✓</span>{` /forge skill installed\n`}
          {`  `}<span className="text-forge-emerald">✓</span>{` /forgeignore skill installed\n\n`}
          <span className="text-[#4E586E]">{`  …\n\n`}</span>
        </Block>

        {/* Green summary panel */}
        <Block i={5}>
          <span className="text-forge-emerald">{`╭─ Configuration `}</span>
          <span className="text-forge-emerald">{`─`.repeat(37)}</span>
          <span className="text-forge-emerald">{`╮`}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`                                                    `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`  API Key:       sk-or-v1****                         `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`  Dashboard:     `}
          <span className="text-forge-emerald">Enabled</span>
          {`                              `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`  Data Sharing:  `}
          <span className="text-forge-emerald">Enabled</span>
          {`                              `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`  Claude Code:   `}
          <span className="text-forge-emerald">Integrated (user scope)</span>
          {`              `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`  Config:        ~/.vibe2prod/config.json          `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`                                                    `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`  `}<span className="font-bold text-forge-emerald">Setup complete!</span>
          {`                                   `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`  Next: vibe2prod scan ./your-project              `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{"│"}</span>
          {`                                                    `}
          <span className="text-forge-emerald">{"│"}</span>{"\n"}
          <span className="text-forge-emerald">{`╰`}</span>
          <span className="text-forge-emerald">{`─`.repeat(52)}</span>
          <span className="text-forge-emerald">{`╯`}</span>
        </Block>

        {/* Blinking cursor */}
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, repeatType: "reverse" }}
          className="inline-block ml-1 text-forge-emerald"
        >
          ▊
        </motion.span>
      </pre>
    </div>
  );
}
