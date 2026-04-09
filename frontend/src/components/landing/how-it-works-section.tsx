"use client";

import { useRef } from "react";
import { motion, useScroll, useTransform } from "motion/react";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";

export function HowItWorksSection() {
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.8", "end 0.6"],
  });
  const lineHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

  const steps = [
    {
      num: "01",
      title: "Install the MCP server",
      desc: "pip install forge-engine, then `claude mcp add forge -e OPENROUTER_API_KEY=… -- python -m forge.mcp_server`. Works in any Claude Code session.",
    },
    {
      num: "02",
      title: "Run /forge in Claude Code",
      desc: "The slash skill calls forge_scan: 16 Opengrep rules plus two LLM passes (Codebase Analyst + Security Auditor) audit your repo.",
    },
    {
      num: "03",
      title: "Triage + suppress false positives",
      desc: "The skill walks each finding, you decide — real issues stay, false positives become structured .forgeignore v2 entries that persist across scans.",
    },
    {
      num: "04",
      title: "Fix + rescan until clean",
      desc: "Claude applies the fixes against the remaining findings, then reruns the scan to verify. Nothing merges until the report is green.",
    },
  ];

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
          {/* Animated connecting line — draws on scroll */}
          <div className="absolute left-8 top-0 bottom-0 w-px bg-white/[0.06] hidden md:block">
            <motion.div
              className="w-full bg-gradient-to-b from-forge-emerald to-forge-teal"
              style={{ height: lineHeight }}
            />
          </div>

          <div className="space-y-12">
            {steps.map((step, i) => (
              <FadeInWhenVisible key={step.num} delay={i * 0.15}>
                <div className="flex items-start gap-8">
                  <motion.div
                    className="shrink-0 w-16 h-16 rounded-2xl bg-forge-emerald/10 border border-forge-emerald/20 flex items-center justify-center font-[family-name:var(--font-heading)] text-forge-emerald font-bold text-xl relative z-10"
                    whileHover={{
                      scale: 1.1,
                      borderColor: "rgba(52,211,153,0.5)",
                    }}
                    transition={{
                      type: "spring",
                      stiffness: 300,
                      damping: 20,
                    }}
                  >
                    {step.num}
                  </motion.div>
                  <div className="pt-2">
                    <h3 className="text-xl font-bold mb-2 font-[family-name:var(--font-heading)]">
                      {step.title}
                    </h3>
                    <p className="text-[#8692A8]">{step.desc}</p>
                  </div>
                </div>
              </FadeInWhenVisible>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
