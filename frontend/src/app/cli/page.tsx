"use client";

import { useRef, useState, useEffect } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform, AnimatePresence } from "motion/react";
import {
  Terminal,
  Shield,
  Zap,
  DollarSign,
  Copy,
  Check,
  ArrowRight,
  Lock,
  GitBranch,
  ExternalLink,
} from "lucide-react";

export const dynamic = "force-dynamic";

/* ────────────── Typing Animation ────────────── */

function TerminalLine({
  text,
  delay,
  prefix = "❯",
  color = "text-emerald-400",
  isOutput = false,
}: {
  text: string;
  delay: number;
  prefix?: string;
  color?: string;
  isOutput?: boolean;
}) {
  const [displayed, setDisplayed] = useState("");
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setStarted(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  useEffect(() => {
    if (!started) return;
    if (isOutput) {
      setDisplayed(text);
      return;
    }
    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(interval);
    }, 25);
    return () => clearInterval(interval);
  }, [started, text, isOutput]);

  if (!started) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={`${isOutput ? "text-zinc-500" : color}`}
    >
      {!isOutput && (
        <span className="text-emerald-400 mr-2">{prefix}</span>
      )}
      {isOutput && <span className="ml-5" />}
      {displayed}
      {!isOutput && displayed.length < text.length && (
        <span className="animate-pulse">▌</span>
      )}
    </motion.div>
  );
}

/* ────────────── Copy Button ────────────── */

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="absolute top-3 right-3 p-1.5 rounded-md bg-zinc-800/80 hover:bg-zinc-700 transition-colors group"
      title="Copy to clipboard"
    >
      <AnimatePresence mode="wait">
        {copied ? (
          <motion.div key="check" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
            <Check className="w-3.5 h-3.5 text-emerald-400" />
          </motion.div>
        ) : (
          <motion.div key="copy" initial={{ scale: 0 }} animate={{ scale: 1 }} exit={{ scale: 0 }}>
            <Copy className="w-3.5 h-3.5 text-zinc-400 group-hover:text-zinc-200" />
          </motion.div>
        )}
      </AnimatePresence>
    </button>
  );
}

/* ────────────── Step Card ────────────── */

function StepCard({
  step,
  title,
  command,
  description,
  delay,
}: {
  step: number;
  title: string;
  command: string;
  description: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.5 }}
      className="flex-1 relative group"
    >
      <div className="relative bg-zinc-900/60 backdrop-blur-sm border border-zinc-800 rounded-xl p-6 h-full hover:border-emerald-500/30 transition-colors duration-300">
        <div className="w-10 h-10 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
          <span className="text-emerald-400 font-bold font-mono text-sm">{step}</span>
        </div>
        <h3 className="text-white font-semibold text-lg mb-2 font-[family-name:var(--font-space-grotesk)]">
          {title}
        </h3>
        <code className="text-emerald-400/80 text-xs font-[family-name:var(--font-jetbrains-mono)] bg-zinc-800/60 px-2 py-1 rounded block mb-3">
          {command}
        </code>
        <p className="text-zinc-400 text-sm leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

/* ────────────── Feature Card ────────────── */

function FeatureCard({
  icon: Icon,
  title,
  value,
  description,
  delay,
}: {
  icon: typeof Shield;
  title: string;
  value: string;
  description: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true }}
      transition={{ delay, duration: 0.5 }}
      className="flex-1"
    >
      <div className="bg-zinc-900/40 border border-zinc-800/50 rounded-xl p-5 hover:border-emerald-500/20 transition-colors duration-300">
        <Icon className="w-5 h-5 text-emerald-400 mb-3" />
        <div className="text-emerald-400 text-2xl font-bold font-[family-name:var(--font-space-grotesk)] mb-1">
          {value}
        </div>
        <div className="text-white text-sm font-medium mb-1">{title}</div>
        <p className="text-zinc-500 text-xs leading-relaxed">{description}</p>
      </div>
    </motion.div>
  );
}

/* ────────────── Main Page ────────────── */

export default function CLIPage() {
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const heroOpacity = useTransform(scrollYProgress, [0, 1], [1, 0]);
  const heroY = useTransform(scrollYProgress, [0, 1], [0, -50]);

  return (
    <div className="min-h-screen bg-[#0a0e17] text-white overflow-hidden">
      {/* ── Background Effects ── */}
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

      {/* ── Nav ── */}
      <nav className="relative z-10 flex items-center justify-between px-6 md:px-12 py-5">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-7 h-7 rounded-md bg-emerald-500 flex items-center justify-center">
            <Terminal className="w-4 h-4 text-[#0a0e17]" />
          </div>
          <span className="text-white font-semibold text-sm font-[family-name:var(--font-space-grotesk)] group-hover:text-emerald-400 transition-colors">
            FORGE
          </span>
          <span className="text-zinc-600 text-xs font-mono ml-1">CLI</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link
            href="https://github.com/christopher-igweze/forge-engine"
            target="_blank"
            className="text-zinc-400 hover:text-white text-sm transition-colors flex items-center gap-1"
          >
            <GitBranch className="w-3.5 h-3.5" />
            GitHub
          </Link>
          <Link
            href="/"
            className="text-zinc-400 hover:text-white text-sm transition-colors"
          >
            Cloud Platform
          </Link>
        </div>
      </nav>

      {/* ── Hero ── */}
      <motion.section
        ref={heroRef}
        style={{ opacity: heroOpacity, y: heroY }}
        className="relative z-10 px-6 md:px-12 pt-16 pb-20 max-w-4xl mx-auto text-center"
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/20 bg-emerald-500/5 mb-6">
            <Lock className="w-3 h-3 text-emerald-400" />
            <span className="text-emerald-400 text-xs font-medium tracking-wide">
              100% LOCAL — YOUR CODE NEVER LEAVES YOUR MACHINE
            </span>
          </div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6 }}
          className="text-4xl md:text-6xl font-bold leading-[1.1] mb-4 font-[family-name:var(--font-space-grotesk)]"
        >
          Your code. Your machine.
          <br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300">
            Full audit.
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="text-zinc-400 text-lg md:text-xl max-w-2xl mx-auto mb-10 leading-relaxed"
        >
          FORGE scans your codebase for security vulnerabilities, code quality
          issues, and architectural problems — then your AI assistant fixes
          them.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="flex items-center justify-center gap-3"
        >
          <a
            href="#get-started"
            className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-400 text-[#0a0e17] font-semibold px-6 py-3 rounded-lg transition-colors text-sm"
          >
            Get Started
            <ArrowRight className="w-4 h-4" />
          </a>
          <a
            href="https://github.com/christopher-igweze/forge-engine"
            target="_blank"
            className="inline-flex items-center gap-2 border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white px-6 py-3 rounded-lg transition-colors text-sm"
          >
            <GitBranch className="w-4 h-4" />
            View on GitHub
          </a>
        </motion.div>
      </motion.section>

      {/* ── 3-Step Flow ── */}
      <section className="relative z-10 px-6 md:px-12 pb-20 max-w-4xl mx-auto">
        <div className="flex flex-col md:flex-row gap-4">
          <StepCard
            step={1}
            title="Install"
            command="pip install vibe2prod"
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

      {/* ── Terminal Demo ── */}
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
              <CopyButton text={`pip install vibe2prod\nclaude mcp add forge -- python -m forge.mcp_server`} />

              <TerminalLine text='pip install vibe2prod' delay={500} />
              <TerminalLine text="  Successfully installed vibe2prod-1.2.0" delay={1500} isOutput />

              <TerminalLine text='claude mcp add forge -- python -m forge.mcp_server' delay={2500} />
              <TerminalLine text="  Added MCP server: forge" delay={3500} isOutput />

              <div className="h-3" />
              <TerminalLine text='"Scan my codebase with forge"' delay={4500} color="text-white" />
              <TerminalLine text="  Scanning 184 files..." delay={5500} isOutput />
              <TerminalLine text="  Security: 8 issues (2 critical, 3 high)" delay={6200} isOutput />
              <TerminalLine text="  Quality: 12 issues" delay={6800} isOutput />
              <TerminalLine text="  Architecture: 5 issues" delay={7300} isOutput />
              <TerminalLine text="  ✓ 42 findings | Readiness: 58/100 | $1.20 | 8 min" delay={7800} color="text-emerald-400" isOutput />

              <div className="h-3" />
              <TerminalLine text="/forge" delay={9000} />
              <TerminalLine text="  Reading scan report... 42 findings" delay={10000} isOutput />
              <TerminalLine text="  Fixing [critical] SQL injection in auth.py..." delay={10800} isOutput />
              <TerminalLine text="  Fixing [high] Missing error handling in routes.py..." delay={11500} isOutput />
              <TerminalLine text="  Fixing [high] Hardcoded secrets in config.py..." delay={12200} isOutput />
              <TerminalLine text="  ✓ 38 fixed | Readiness: 94/100" delay={13000} color="text-emerald-400" isOutput />
            </div>
          </div>
        </motion.div>
      </section>

      {/* ── Features ── */}
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

      {/* ── Get Started ── */}
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
          <h2 className="text-2xl font-bold mb-6 font-[family-name:var(--font-space-grotesk)]">
            Quick Start
          </h2>
          <div className="space-y-4 font-[family-name:var(--font-jetbrains-mono)] text-sm">
            <div>
              <div className="text-zinc-500 text-xs mb-1">1. Install FORGE</div>
              <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800 relative group">
                <code className="text-emerald-400">pip install vibe2prod</code>
                <CopyButton text="pip install vibe2prod" />
              </div>
            </div>
            <div>
              <div className="text-zinc-500 text-xs mb-1">
                2. Add your OpenRouter API key
              </div>
              <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800 relative group">
                <code className="text-emerald-400">
                  export OPENROUTER_API_KEY=sk-or-v1-...
                </code>
                <CopyButton text="export OPENROUTER_API_KEY=sk-or-v1-your-key-here" />
              </div>
            </div>
            <div>
              <div className="text-zinc-500 text-xs mb-1">
                3. Register the MCP server
              </div>
              <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800 relative group">
                <code className="text-emerald-400">
                  claude mcp add forge -- python -m forge.mcp_server
                </code>
                <CopyButton text="claude mcp add forge -- python -m forge.mcp_server" />
              </div>
            </div>
            <div>
              <div className="text-zinc-500 text-xs mb-1">
                4. Scan and fix
              </div>
              <div className="bg-[#0d1117] rounded-lg px-4 py-3 border border-zinc-800">
                <code className="text-zinc-400">
                  In Claude Code:{" "}
                  <span className="text-white">
                    &quot;Scan my codebase with forge&quot;
                  </span>{" "}
                  then{" "}
                  <span className="text-emerald-400">/forge</span> to fix
                </code>
              </div>
            </div>
          </div>

          <div className="mt-6 pt-6 border-t border-zinc-800">
            <p className="text-zinc-500 text-xs mb-3">
              Get an API key at{" "}
              <a
                href="https://openrouter.ai"
                target="_blank"
                className="text-emerald-400 hover:underline"
              >
                openrouter.ai
              </a>
              {" "}— sign up is free, pay per token.
            </p>
          </div>
        </motion.div>
      </section>

      {/* ── Works With ── */}
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

      {/* ── Footer ── */}
      <footer className="relative z-10 border-t border-zinc-800/50 px-6 md:px-12 py-8 max-w-4xl mx-auto">
        <div className="flex items-center justify-between text-zinc-600 text-xs">
          <span>
            FORGE by{" "}
            <a href="/" className="text-zinc-400 hover:text-white transition-colors">
              Vibe2Prod
            </a>
          </span>
          <div className="flex gap-4">
            <a
              href="https://github.com/christopher-igweze/forge-engine"
              target="_blank"
              className="hover:text-zinc-400 transition-colors flex items-center gap-1"
            >
              GitHub <ExternalLink className="w-3 h-3" />
            </a>
            <Link href="/" className="hover:text-zinc-400 transition-colors">
              Cloud Platform
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
