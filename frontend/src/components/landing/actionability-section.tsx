"use client";

import { motion } from "motion/react";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";

export function ActionabilitySection() {
  const tiers = [
    {
      label: "Must Fix",
      color: "text-red-400 bg-red-500/10 border-red-500/20",
      description: "Exploitable vulnerabilities \u2014 fix before shipping",
    },
    {
      label: "Should Fix",
      color: "text-orange-400 bg-orange-500/10 border-orange-500/20",
      description: "Real issues \u2014 prioritize this sprint",
    },
    {
      label: "Consider",
      color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
      description: "Valid observations \u2014 address when convenient",
    },
    {
      label: "Informational",
      color: "text-blue-400 bg-blue-500/10 border-blue-500/20",
      description: "Noted for awareness \u2014 no action needed",
    },
  ];

  return (
    <section className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)]">
            Not Just Severity &mdash;{" "}
            <span className="forge-gradient-text">Actionability</span>
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-12 max-w-2xl mx-auto">
            Every finding is classified by what you should actually do about it,
            calibrated to your project&apos;s stage and context.
          </p>
        </FadeInWhenVisible>
        <div className="grid sm:grid-cols-2 gap-4">
          {tiers.map((tier, i) => (
            <FadeInWhenVisible key={tier.label} delay={i * 0.1}>
              <motion.div
                className={`rounded-xl border p-5 ${tier.color}`}
                whileHover={{ scale: 1.03, y: -4 }}
                transition={{ type: "spring", stiffness: 300, damping: 25 }}
              >
                <div className="font-semibold mb-1">{tier.label}</div>
                <div className="text-sm opacity-80">{tier.description}</div>
              </motion.div>
            </FadeInWhenVisible>
          ))}
        </div>
      </div>
    </section>
  );
}
