"use client";

import { Search, Wrench, ShieldCheck } from "lucide-react";
import {
  FadeInWhenVisible,
  TiltCard,
} from "@/components/landing/motion-primitives";

export function FeaturesSection() {
  const features = [
    {
      title: "Discover",
      subtitle: "Opengrep + 4 discovery agents.",
      description:
        "Deterministic Opengrep static analysis plus a codebase analyst, security auditor, quality auditor, and architecture reviewer running in parallel. Findings scored with AIVSS and deduped against a vulnerability pattern library tuned for AI-generated apps (client-writable Supabase columns, missing RLS, leaked keys).",
      icon: Search,
    },
    {
      title: "Fix",
      subtitle: "Triage + 4-agent remediation swarm.",
      description:
        "A fix strategist and triage classifier sort findings into complexity tiers, then Tier 2/3 coders, a test generator, and a code reviewer apply fixes through three control loops \u2014 inner retry (max 3), escalation, and replan. Auto-applies patches and reruns until clean.",
      icon: Wrench,
    },
    {
      title: "Validate",
      subtitle: "2 validation agents. 0\u2013100 score.",
      description:
        "An integration validator confirms fixes don\u2019t break the build and a debt tracker returns a Production Readiness Score (0\u2013100) with category breakdowns across security, reliability, quality, and operations.",
      icon: ShieldCheck,
    },
  ];

  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)]">
            12 agents. 4 phases. One pipeline.
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-16 max-w-2xl mx-auto">
            CodeQL and Snyk hand you a report. Vibe2Prod applies the patches,
            reruns the scan, and hands you back production-ready code.
          </p>
        </FadeInWhenVisible>

        <div className="space-y-16 md:space-y-24">
          {features.map((feature, i) => (
            <FadeInWhenVisible
              key={feature.title}
              delay={i * 0.15}
              className={`flex flex-col ${
                i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              } items-center gap-8 md:gap-16`}
            >
              {/* Icon block with 3D tilt */}
              <div
                className="flex-1 flex items-center justify-center"
                style={{ perspective: "800px" }}
              >
                <TiltCard className="relative w-52 h-52 sm:w-64 sm:h-64 rounded-3xl forge-glass-card forge-gradient-border flex items-center justify-center">
                  <feature.icon
                    className="size-16 sm:size-20 text-forge-emerald"
                    strokeWidth={1.5}
                  />
                  {/* Floating number badge — pops out in 3D */}
                  <div
                    className="absolute -top-3 -left-3 w-10 h-10 rounded-full bg-forge-emerald text-[#0B0F19] flex items-center justify-center font-bold text-lg font-[family-name:var(--font-heading)]"
                    style={{ transform: "translateZ(30px)" }}
                  >
                    {i + 1}
                  </div>
                  {/* Inner glow on hover */}
                  <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-forge-emerald/10 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-500" />
                </TiltCard>
              </div>

              {/* Text block */}
              <div className="flex-1 text-center md:text-left">
                <h3 className="text-3xl font-bold mb-2 font-[family-name:var(--font-heading)]">
                  {feature.title}
                </h3>
                <p className="text-forge-emerald text-sm font-medium mb-4">
                  {feature.subtitle}
                </p>
                <p className="text-[#8692A8] leading-relaxed">
                  {feature.description}
                </p>
              </div>
            </FadeInWhenVisible>
          ))}
        </div>
      </div>
    </section>
  );
}
