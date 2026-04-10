"use client";

import type { ReactNode } from "react";
import {
  FadeInWhenVisible,
  AnimatedCounter,
} from "@/components/landing/motion-primitives";
import { IconClaude } from "@/components/landing/landing-icons";

export function SocialProofBar() {
  const stats: { value?: number; display?: string; label: ReactNode }[] = [
    { value: 16, label: "Deterministic Opengrep Rules" },
    { value: 2, label: "Targeted LLM Agents" },
    {
      value: 4,
      label: (
        <span className="inline-flex items-center gap-1.5 justify-center">
          MCP Tools In{" "}
          <span className="text-[#D97757] inline-flex items-center gap-1">
            <IconClaude className="size-3.5" />
            Claude&nbsp;Code
          </span>
        </span>
      ),
    },
    { display: "0\u2013100", label: "Production Readiness Score" },
  ];

  return (
    <section className="py-16 border-y border-white/[0.06]">
      <div className="mx-auto max-w-5xl px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((stat, i) => (
            <FadeInWhenVisible key={i} delay={i * 0.1}>
              <div className="text-4xl sm:text-5xl font-bold forge-gradient-text font-[family-name:var(--font-heading)]">
                {stat.value !== undefined ? (
                  <AnimatedCounter target={stat.value} />
                ) : (
                  stat.display
                )}
              </div>
              <div className="text-sm text-[#8692A8] mt-2">{stat.label}</div>
            </FadeInWhenVisible>
          ))}
        </div>
      </div>
    </section>
  );
}
