"use client";

import {
  FadeInWhenVisible,
  AnimatedCounter,
} from "@/components/landing/motion-primitives";

export function SocialProofBar() {
  const stats: { value?: number; display?: string; label: string }[] = [
    { value: 12, label: "AI Agents Working In Parallel" },
    { value: 3, label: "Self-Healing Control Loops" },
    { display: "0\u2013100", label: "Production Readiness Score" },
    { display: "Auto", label: "Fix, Test & Validate" },
  ];

  return (
    <section className="py-16 border-y border-white/[0.06]">
      <div className="mx-auto max-w-5xl px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((stat, i) => (
            <FadeInWhenVisible key={stat.label} delay={i * 0.1}>
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
