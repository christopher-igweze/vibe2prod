"use client";

import { useRef } from "react";
import Link from "next/link";
import { SignedOut } from "@clerk/nextjs";
import { motion, useScroll, useTransform } from "motion/react";
import { SignedInCTA } from "@/components/landing/signed-in-cta";

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
      className="relative min-h-[90vh] flex items-center justify-center overflow-hidden"
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
          Plug FORGE into Claude Code. One slash command, one clean repo.
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
          Install the FORGE MCP server, run <code className="text-forge-emerald">/forge</code> inside Claude Code, and
          16 Opengrep rules plus two targeted LLM passes audit your repo,
          triage the noise, apply fixes, and rescan until clean &mdash; built
          for Supabase-backed apps from Lovable, Bolt, and v0.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.0 }}
          className="mt-12 flex items-center justify-center gap-4"
        >
          <SignedOut>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Link
                href="/sign-up"
                className="forge-shimmer-cta rounded-xl px-8 py-4 text-lg font-semibold transition-shadow hover:shadow-[0_0_40px_-4px_rgba(52,211,153,0.4)] block"
              >
                Get Started
              </Link>
            </motion.div>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Link
                href="/sign-in"
                className="forge-glass-card rounded-xl px-8 py-4 text-lg font-semibold text-[#E8ECF4] block"
              >
                Sign In
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
