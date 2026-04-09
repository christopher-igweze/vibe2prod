"use client";

import type { ReactNode } from "react";
import { motion } from "motion/react";
import { IconPrompt } from "@/components/landing/landing-icons";

/**
 * Faux terminal rendering of `vibe2prod setup`. Uses CSS bordered
 * panels (not ASCII box drawing) so the frame stays perfectly aligned
 * at any viewport width. Mirrors the Rich output of
 * forge-engine/forge/setup_wizard.py — blue intro panel, 6 steps,
 * green ✓ checkmarks for MCP + skill installation, and the green
 * Configuration summary.
 */

const blockVariants = {
  hidden: { opacity: 0, y: 10 },
  show: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: 0.15 + i * 0.22,
      duration: 0.45,
      ease: [0.25, 0.46, 0.45, 0.94] as const,
    },
  }),
};

function Block({ i, children }: { i: number; children: ReactNode }) {
  return (
    <motion.div
      custom={i}
      variants={blockVariants}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: "-100px" }}
    >
      {children}
    </motion.div>
  );
}

interface PanelProps {
  title: string;
  accent: "blue" | "emerald";
  children: ReactNode;
}

function Panel({ title, accent, children }: PanelProps) {
  const border = accent === "blue" ? "border-blue-400/50" : "border-forge-emerald/55";
  const titleColor = accent === "blue" ? "text-blue-300" : "text-forge-emerald";
  return (
    <div className={`relative mt-3 mb-1 rounded-md border ${border} px-5 py-5 sm:px-6 sm:py-6`}>
      <div
        className={`absolute -top-[9px] left-4 bg-[#0a0e17] px-2 text-[11px] font-medium ${titleColor}`}
      >
        {title}
      </div>
      {children}
    </div>
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
          <IconPrompt className="size-3" />
          <span>vibe2prod setup</span>
        </div>
      </div>

      {/* Terminal body — monospace block with CSS panels */}
      <div className="px-5 sm:px-7 py-5 sm:py-6 font-mono text-[12px] sm:text-[13px] leading-[1.6] text-[#E8ECF4]">
        <Block i={0}>
          <div className="mb-2">
            <span className="text-forge-emerald">$</span> vibe2prod setup
          </div>
        </Block>

        {/* Blue intro panel */}
        <Block i={1}>
          <Panel title="vibe2prod" accent="blue">
            <div className="font-bold text-blue-300 mb-3">FORGE Setup Wizard</div>
            <div className="text-[#E8ECF4] leading-relaxed">
              Configure FORGE for local code auditing.
              <br />
              Your code never leaves your machine &mdash; only LLM API calls go
              to OpenRouter.
            </div>
          </Panel>
        </Block>

        {/* Step 1 */}
        <Block i={2}>
          <div className="mt-5">
            <div>
              <span className="font-bold text-[#E8ECF4]">
                Step 1/6 &mdash; OpenRouter API Key
              </span>
              <span className="text-[#8692A8]"> (optional)</span>
            </div>
            <div className="pl-4 mt-1 text-[#8692A8]">
              Enter your OpenRouter API key (press Enter to skip)
            </div>
            <div className="pl-4 text-[#8692A8]">
              Get yours at: https://openrouter.ai/keys
            </div>
            <div className="pl-4 mt-3">
              OpenRouter API key:{" "}
              <span className="text-[#4E586E]">••••••••••••••••••••</span>
            </div>
          </div>
        </Block>

        {/* Step 2 + 3 */}
        <Block i={3}>
          <div className="mt-5">
            <div>
              <span className="font-bold text-[#E8ECF4]">
                Step 2/6 &mdash; Vibe2Prod Dashboard
              </span>
              <span className="text-[#8692A8]"> (optional)</span>
            </div>
            <div className="pl-4 mt-1">
              Enable dashboard sync?{" "}
              <span className="text-[#4E586E]">[Y/n]:</span>{" "}
              <span className="text-forge-emerald">y</span>
            </div>
          </div>

          <div className="mt-5">
            <div className="font-bold text-[#E8ECF4]">
              Step 3/6 &mdash; Data Sharing
            </div>
            <div className="pl-4 mt-1">
              Share anonymized suppression data?{" "}
              <span className="text-[#4E586E]">[Y/n]:</span>{" "}
              <span className="text-forge-emerald">y</span>
            </div>
          </div>
        </Block>

        {/* Step 4 — the money shot */}
        <Block i={4}>
          <div className="mt-5">
            <div className="font-bold text-[#E8ECF4]">
              Step 4/6 &mdash; Claude Code Integration
            </div>
            <div className="pl-4 mt-1">
              <span className="text-forge-emerald">Claude Code detected!</span>
            </div>
            <div className="pl-4">
              Register FORGE as MCP server + install skills?{" "}
              <span className="text-[#4E586E]">[Y/n]:</span>{" "}
              <span className="text-forge-emerald">y</span>
            </div>
            <div className="pl-4">
              Register for all projects (user) or just this one?{" "}
              <span className="text-forge-emerald">user</span>
            </div>
            <div className="pl-4 text-[#4E586E]">
              ⠋ Registering MCP server...
            </div>
            <div className="pl-4">
              <span className="text-forge-emerald">✓</span>{" "}
              MCP server registered (user scope)
            </div>
            <div className="pl-4">
              <span className="text-forge-emerald">✓</span>{" "}
              /forge skill installed
            </div>
            <div className="pl-4">
              <span className="text-forge-emerald">✓</span>{" "}
              /forgeignore skill installed
            </div>
            <div className="pl-4 mt-3 text-[#4E586E]">…</div>
          </div>
        </Block>

        {/* Green Configuration panel */}
        <Block i={5}>
          <div className="mt-5">
            <Panel title="Configuration" accent="emerald">
              <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
                <div className="text-[#8692A8]">API Key:</div>
                <div>sk-or-v1****</div>

                <div className="text-[#8692A8]">Dashboard:</div>
                <div className="text-forge-emerald">Enabled</div>

                <div className="text-[#8692A8]">Data Sharing:</div>
                <div className="text-forge-emerald">Enabled</div>

                <div className="text-[#8692A8]">Claude Code:</div>
                <div className="text-forge-emerald">
                  Integrated (user scope)
                </div>

                <div className="text-[#8692A8]">Config:</div>
                <div>~/.vibe2prod/config.json</div>
              </div>

              <div className="mt-4 font-bold text-forge-emerald">
                Setup complete!
              </div>
              <div className="text-[#E8ECF4]">
                Next: <span className="text-forge-emerald">vibe2prod scan ./your-project</span>
              </div>
            </Panel>
          </div>
        </Block>

        {/* Blinking cursor */}
        <motion.span
          animate={{ opacity: [1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity, repeatType: "reverse" }}
          className="inline-block mt-2 text-forge-emerald"
        >
          ▊
        </motion.span>
      </div>
    </div>
  );
}
