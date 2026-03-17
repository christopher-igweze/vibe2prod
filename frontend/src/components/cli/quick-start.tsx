"use client";

import { motion } from "motion/react";
import { Zap, Shield } from "lucide-react";
import { CopyButton } from "./terminal-primitives";

export function QuickStart() {
  return (
    <section
      id="get-started"
      className="relative z-10 px-6 md:px-12 pb-20 max-w-4xl mx-auto"
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="bg-zinc-900/40 border border-zinc-800 rounded-xl p-8 md:p-10"
      >
        <h2 className="text-2xl font-bold mb-2 font-[family-name:var(--font-space-grotesk)]">
          Quick Start
        </h2>
        <p className="text-zinc-500 text-sm mb-6">
          You need an{" "}
          <a href="https://openrouter.ai" target="_blank" className="text-emerald-400 hover:underline">
            OpenRouter API key
          </a>{" "}
          (free signup, pay per token).
        </p>
        <div className="space-y-4 font-[family-name:var(--font-jetbrains-mono)] text-sm">
          <div>
            <div className="text-zinc-500 text-xs mb-1">1. Install FORGE</div>
            <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800 relative group">
              <code className="text-emerald-400">pip3 install vibe2prod</code>
              <CopyButton text="pip3 install vibe2prod" />
            </div>
          </div>
          <div>
            <div className="text-zinc-500 text-xs mb-1">
              2. Add MCP server with your API key
            </div>
            <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800 relative group">
              <pre className="text-emerald-400 text-xs leading-relaxed whitespace-pre-wrap"><code>{`claude mcp add forge \\
  -e OPENROUTER_API_KEY=sk-or-v1-your-key \\
  -- forge-mcp`}</code></pre>
              <CopyButton text="claude mcp add forge -e OPENROUTER_API_KEY=sk-or-v1-your-key -- forge-mcp" />
            </div>
            <div className="text-zinc-600 text-xs mt-2 ml-1">
              Optional: sync scans to your dashboard
            </div>
            <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800/50 mt-1.5">
              <pre className="text-zinc-500 text-xs leading-relaxed whitespace-pre-wrap"><code>{`# Add these flags before the -- separator:
  -e VIBE2PROD_API_KEY=v2p_your-key \\`}</code></pre>
            </div>
          </div>
          <div>
            <div className="text-zinc-500 text-xs mb-1">
              3. Install the /forge skill (enables auto-fixing)
            </div>
            <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800 relative group">
              <code className="text-emerald-400 text-xs">
                mkdir -p ~/.claude/skills/forge && curl -sL https://vibe2prod.net/forge-skill.md -o ~/.claude/skills/forge/SKILL.md
              </code>
              <CopyButton text="mkdir -p ~/.claude/skills/forge && curl -sL https://vibe2prod.net/forge-skill.md -o ~/.claude/skills/forge/SKILL.md" />
            </div>
          </div>
          <div>
            <div className="text-zinc-500 text-xs mb-1">
              4. Use it
            </div>
            <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800 space-y-1">
              <code className="text-zinc-400 block">
                In Claude Code:{" "}
                <span className="text-white">
                  &quot;Scan my codebase with forge&quot;
                </span>
              </code>
              <code className="text-zinc-400 block">
                Then:{" "}
                <span className="text-emerald-400">/forge</span>
                {" "}to fix all findings automatically
              </code>
            </div>
          </div>
        </div>

        <div className="mt-6 pt-6 border-t border-zinc-800 space-y-3">
          <p className="text-zinc-500 text-xs">
            <span className="text-zinc-400 font-medium">No API key?</span>{" "}
            The scan will show a clear error message asking you to set one up.
          </p>
          <p className="text-zinc-500 text-xs">
            <span className="text-zinc-400 font-medium">Usage tracking:</span>{" "}
            Anonymous scan metrics only (finding counts, not code). Opt-in data sharing available for improving FORGE.
          </p>
        </div>
      </motion.div>
    </section>
  );
}

export function DashboardConnect() {
  return (
    <section className="relative z-10 px-6 md:px-12 pb-20 max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="bg-zinc-900/30 border border-zinc-800/50 rounded-xl p-8 md:p-10"
      >
        <h2 className="text-xl font-bold mb-1 font-[family-name:var(--font-space-grotesk)]">
          Optional: Connect to Dashboard
        </h2>
        <p className="text-zinc-500 text-sm mb-6">
          FORGE works fully offline. Add an API key to sync scan results to your dashboard.
        </p>

        <div className="grid md:grid-cols-2 gap-6">
          {/* Dashboard Sync */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <Zap className="w-4 h-4 text-emerald-400" />
              </div>
              <h3 className="text-white font-semibold text-sm font-[family-name:var(--font-space-grotesk)]">
                Dashboard Sync
              </h3>
            </div>
            <div className="text-zinc-400 text-xs leading-relaxed space-y-3">
              <div className="space-y-1.5">
                <p className="text-zinc-300 font-medium">3 steps:</p>
                <ol className="list-decimal list-inside space-y-1">
                  <li>
                    Create an account at{" "}
                    <a href="https://vibe2prod.net" target="_blank" className="text-emerald-400 hover:underline">
                      vibe2prod.net
                    </a>
                  </li>
                  <li>
                    Go to{" "}
                    <a href="https://vibe2prod.net/settings" target="_blank" className="text-emerald-400 hover:underline">
                      Settings
                    </a>
                    {" "}and click <span className="text-zinc-300">Generate API Key</span>
                  </li>
                  <li>Add the key to your MCP setup (see below)</li>
                </ol>
              </div>
              <div className="bg-[#0d1117] rounded-lg px-3 py-2.5 border border-zinc-800">
                <pre className="text-emerald-400/80 text-[11px] leading-relaxed whitespace-pre-wrap font-[family-name:var(--font-jetbrains-mono)]"><code>{`claude mcp add forge \\
  -e OPENROUTER_API_KEY=sk-or-... \\
  -e VIBE2PROD_API_KEY=v2p_... \\
  -- forge-mcp`}</code></pre>
              </div>
              <p>CLI scans appear in your dashboard alongside cloud scans, grouped by repo with readiness trends over time.</p>
            </div>
          </div>

          {/* Data Sharing */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                <Shield className="w-4 h-4 text-emerald-400" />
              </div>
              <h3 className="text-white font-semibold text-sm font-[family-name:var(--font-space-grotesk)]">
                Data Sharing (Opt-in)
              </h3>
            </div>
            <div className="text-zinc-400 text-xs leading-relaxed space-y-1.5">
              <p>
                Add <code className="text-emerald-400/80 bg-zinc-800/60 px-1 py-0.5 rounded">VIBE2PROD_DATA_SHARING=true</code> to your MCP setup
              </p>
              <p>Shares anonymized finding patterns (types, severities, fix rates)</p>
              <p className="text-zinc-500 font-medium">
                NEVER shares code, file paths, or repo identity
              </p>
              <p>Helps improve FORGE&apos;s detection accuracy for everyone</p>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  );
}
