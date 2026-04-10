"use client";

import { useRef, useState } from "react";
import Link from "next/link";
import { SignedOut } from "@clerk/nextjs";
import { motion, useScroll, useTransform } from "motion/react";
import { Check, Copy } from "lucide-react";
import { SignedInCTA } from "@/components/landing/signed-in-cta";

const INSTALL_LINES = [
  "pip install vibe2prod",
  "vibe2prod setup",
];

function CopyableTerminal() {
  const [copied, setCopied] = useState(false);
  const handleCopy = () => {
    navigator.clipboard?.writeText(INSTALL_LINES.join("\n"));
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 1.1 }}
      className="mt-10 mx-auto max-w-2xl"
    >
      <div className="relative rounded-xl border border-white/[0.08] bg-[#0a0e17]/90 backdrop-blur-sm text-left shadow-[0_0_40px_-12px_rgba(52,211,153,0.15)]">
        <div className="flex items-center gap-1.5 px-4 py-2 border-b border-white/[0.06]">
          <span className="size-2.5 rounded-full bg-[#ff5f56]/70" />
          <span className="size-2.5 rounded-full bg-[#ffbd2e]/70" />
          <span className="size-2.5 rounded-full bg-[#27c93f]/70" />
          <span className="ml-auto text-[11px] text-[#4E586E] font-mono">install forge</span>
          <button
            type="button"
            onClick={handleCopy}
            aria-label="Copy install commands"
            className="ml-2 p-1 rounded text-[#4E586E] hover:text-forge-emerald hover:bg-white/[0.04] transition-colors"
          >
            {copied ? <Check className="size-3.5" /> : <Copy className="size-3.5" />}
          </button>
        </div>
        <div className="px-5 py-4 font-mono text-[13px] sm:text-sm leading-relaxed text-[#E8ECF4] overflow-x-auto">
          {INSTALL_LINES.map((line) => (
            <div key={line} className="whitespace-nowrap">
              <span className="text-forge-emerald">$</span>{" "}
              <span>{line}</span>
            </div>
          ))}
        </div>
      </div>
      <p className="mt-3 text-xs text-[#4E586E] text-center">
        Then run <code className="text-forge-emerald">/forge</code> inside Claude Code. Or skip the CLI and use the web UI.
      </p>
    </motion.div>
  );
}

export function HeroSection() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, -150]);
  const orbY = useTransform(scrollYProgress, [0, 1], [0, 100]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  const words = [
    { text: "Discover.", gradient: false },
    { text: "Fix.", gradient: true },
    { text: "Ship.", gradient: false },
  ];

  return (
    <section
      ref={ref}
      className="relative min-h-[90vh] flex items-center justify-center overflow-hidden py-20"
    >
      {/* Animated gradient mesh background */}
      <div className="absolute inset-0 forge-mesh-bg" />

      {/* Floating orbs — parallax drift downward on scroll */}
      <motion.div style={{ y: orbY }} className="absolute inset-0 pointer-events-none">
        <motion.div
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-forge-emerald/15 rounded-full blur-3xl"
          animate={{ y: [-20, 20, -20], scale: [1, 1.05, 1] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-forge-teal/15 rounded-full blur-3xl"
          animate={{ y: [15, -15, 15], scale: [1.05, 1, 1.05] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute top-1/3 right-1/3 w-64 h-64 bg-forge-blue/10 rounded-full blur-3xl"
          animate={{ y: [-10, 25, -10], x: [-10, 10, -10] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        />
      </motion.div>

      {/* Dot grid overlay */}
      <div className="absolute inset-0 forge-dot-grid opacity-40" />

      {/* Hero content — parallax upward + fade on scroll */}
      <motion.div
        style={{ y: heroY, opacity }}
        className="relative mx-auto max-w-4xl px-6 text-center"
      >
        {/* Pill badge */}
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="inline-flex items-center rounded-full border border-forge-emerald/20 bg-forge-emerald/10 px-4 py-1.5 text-sm text-forge-emerald mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-forge-emerald mr-2 animate-pulse" />
          Audit and fix AI-generated apps, right inside Claude Code
        </motion.div>

        {/* Hero headline — staggered word reveal with blur-to-sharp */}
        <h1 className="text-6xl sm:text-7xl lg:text-8xl font-bold tracking-tight font-[family-name:var(--font-heading)] leading-[1.05] overflow-visible">
          {words.map((word, i) => (
            <motion.span
              key={word.text}
              initial={{ opacity: 0, y: 30, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{
                duration: 0.6,
                delay: 0.3 + i * 0.2,
                ease: [0.25, 0.46, 0.45, 0.94],
              }}
              className={word.gradient ? "forge-gradient-text" : "text-foreground"}
              style={{ display: "inline-block", marginRight: "0.3em" }}
            >
              {word.text}
            </motion.span>
          ))}
        </h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="mt-8 text-lg sm:text-xl text-[#8692A8] max-w-2xl mx-auto leading-relaxed"
        >
          FORGE is a CLI + MCP server for Claude Code. 16 Opengrep rules plus
          two targeted LLM agents audit your repo, triage the noise, apply
          fixes, and rescan until clean. Built for the solo builder shipping
          Supabase apps from Lovable, Bolt, and v0.
        </motion.p>

        {/* Install command terminal */}
        <CopyableTerminal />

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.3 }}
          className="mt-10 flex items-center justify-center gap-4 flex-wrap"
        >
          <SignedOut>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Link
                href="#setup"
                className="forge-shimmer-cta rounded-xl px-8 py-4 text-lg font-semibold transition-shadow hover:shadow-[0_0_40px_-4px_rgba(52,211,153,0.4)] block"
              >
                Install guide
              </Link>
            </motion.div>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Link
                href="/sign-up"
                className="forge-glass-card rounded-xl px-8 py-4 text-lg font-semibold text-[#E8ECF4] block"
              >
                Or use the web UI →
              </Link>
            </motion.div>
          </SignedOut>
          <SignedInCTA variant="hero" />
        </motion.div>
      </motion.div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0B0F19] to-transparent" />
    </section>
  );
}
