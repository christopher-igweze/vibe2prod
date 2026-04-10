"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform, type MotionValue } from "motion/react";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";

const STEPS = [
  {
    num: "01",
    title: "Install the CLI",
    desc: "pip install vibe2prod brings down the CLI, the MCP server, and the bundled /forge + /forgeignore skills.",
  },
  {
    num: "02",
    title: "Run the setup wizard",
    desc: "`vibe2prod setup` detects Claude Code, registers the MCP tools, and copies the slash skills into ~/.claude/commands/.",
  },
  {
    num: "03",
    title: "Run /forge in your repo",
    desc: "The skill calls forge_scan (16 Opengrep rules plus two targeted LLM agents) and walks you through every finding.",
  },
  {
    num: "04",
    title: "Fix + rescan until clean",
    desc: "False positives land in .forgeignore as structured entries. Real issues get patched, then the scan reruns to verify.",
  },
];

/**
 * Renders a single step with number block + text.
 * Reads its own reveal progress from the parent scrollYProgress and uses
 * it to pulse/highlight when the line has passed its center.
 */
function Step({
  num,
  title,
  desc,
  index,
  total,
  progress,
}: {
  num: string;
  title: string;
  desc: string;
  index: number;
  total: number;
  progress: MotionValue<number>;
}) {
  // Each step becomes "active" in a narrow range around its vertical slot.
  // The first step at ~0.1, then evenly spaced out to ~0.95.
  const start = 0.08 + (index / total) * 0.82;
  const end = start + 0.1;

  const activeness = useTransform(progress, [start, end], [0, 1]);
  const scale = useTransform(activeness, [0, 1], [1, 1.06]);
  const borderOpacity = useTransform(activeness, [0, 1], [0.18, 0.9]);
  const glowOpacity = useTransform(activeness, [0, 1], [0, 0.55]);

  return (
    <div className="flex items-start gap-6 md:gap-8">
      <motion.div
        style={{
          scale,
          // Border + glow ramp as the line arrives at this step.
          boxShadow: useTransform(
            glowOpacity,
            (o) => `0 0 0 1px rgba(52,211,153,${borderOpacity.get().toFixed(2)}), 0 0 30px rgba(52,211,153,${o.toFixed(2)})`,
          ),
        }}
        className="relative z-10 shrink-0 w-16 h-16 rounded-2xl bg-[#0B0F19] flex items-center justify-center font-[family-name:var(--font-heading)] text-forge-emerald font-bold text-xl"
      >
        {num}
      </motion.div>
      <div className="pt-2 md:pt-3">
        <h3 className="text-xl font-bold mb-2 font-[family-name:var(--font-heading)]">
          {title}
        </h3>
        <p className="text-[#8692A8] leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

export function HowItWorksSection() {
  const containerRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.85", "end 0.55"],
  });
  const lineHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  return (
    <section
      ref={containerRef}
      className="py-24 border-t border-white/[0.06]"
    >
      <div className="mx-auto max-w-5xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-16 font-[family-name:var(--font-heading)]">
            How It Works
          </h2>
        </FadeInWhenVisible>

        <div className="relative">
          {/* Vertical connector — sits BEHIND the step blocks (z-0 vs block's z-10) */}
          <div
            aria-hidden
            className="pointer-events-none absolute left-8 top-6 bottom-6 -translate-x-1/2 w-px bg-white/[0.06] hidden md:block z-0"
          >
            <motion.div
              className="w-full bg-gradient-to-b from-forge-emerald to-forge-teal"
              style={{ height: lineHeight }}
            />
          </div>

          <div className="space-y-12">
            {STEPS.map((step, i) => (
              <FadeInWhenVisible key={step.num} delay={i * 0.1}>
                <Step
                  num={step.num}
                  title={step.title}
                  desc={step.desc}
                  index={i}
                  total={STEPS.length - 1}
                  progress={scrollYProgress}
                />
              </FadeInWhenVisible>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
