"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Copy, Check } from "lucide-react";

/* ────────────── Typing Animation ────────────── */

export function TerminalLine({
  text,
  delay,
  prefix = "\u276F",
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
        <span className="animate-pulse">\u258C</span>
      )}
    </motion.div>
  );
}

/* ────────────── Copy Button ────────────── */

export function CopyButton({ text }: { text: string }) {
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

export function StepCard({
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

export function FeatureCard({
  icon: Icon,
  title,
  value,
  description,
  delay,
}: {
  icon: React.ComponentType<{ className?: string }>;
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
