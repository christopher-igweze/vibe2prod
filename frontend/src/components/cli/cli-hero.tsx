"use client";

import { useRef } from "react";
import Link from "next/link";
import { motion, useScroll, useTransform } from "motion/react";
import { Terminal, Lock, ArrowRight, ExternalLink } from "lucide-react";

export function CLINav() {
  return (
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
        <a
          href="https://openrouter.ai"
          target="_blank"
          className="text-zinc-400 hover:text-white text-sm transition-colors flex items-center gap-1"
        >
          Get API Key
          <ExternalLink className="w-3 h-3" />
        </a>
        <Link
          href="/"
          className="text-zinc-400 hover:text-white text-sm transition-colors"
        >
          Cloud Platform
        </Link>
      </div>
    </nav>
  );
}

export function CLIHero() {
  const heroRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"],
  });
  const heroOpacity = useTransform(scrollYProgress, [0, 1], [1, 0]);
  const heroY = useTransform(scrollYProgress, [0, 1], [0, -50]);

  return (
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
          href="https://openrouter.ai"
          target="_blank"
          className="inline-flex items-center gap-2 border border-zinc-700 hover:border-zinc-500 text-zinc-300 hover:text-white px-6 py-3 rounded-lg transition-colors text-sm"
        >
          Get API Key
          <ExternalLink className="w-3.5 h-3.5" />
        </a>
      </motion.div>
    </motion.section>
  );
}
