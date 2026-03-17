"use client";

import { Check } from "lucide-react";
import { motion } from "motion/react";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";

export function ComparisonSection() {
  const rows = [
    { name: "Find vulnerabilities", others: true, v2p: true },
    { name: "Auto-fix critical issues", others: false, v2p: true },
    { name: "Generate tests for fixes", others: false, v2p: true },
    { name: "Validate fix correctness", others: false, v2p: true },
    { name: "Production readiness score", others: false, v2p: true },
    { name: "Context-aware prioritization", others: false, v2p: true },
    { name: "12-agent orchestration", others: false, v2p: true },
  ];

  return (
    <section className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)]">
            Why Teams Switch to Vibe2Prod
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-12">
            Every other tool stops at detection.{" "}
            <span className="text-forge-emerald font-semibold">
              We go all the way to deployment-ready code.
            </span>
          </p>
        </FadeInWhenVisible>

        <FadeInWhenVisible>
          <div className="forge-glass-card forge-gradient-border rounded-2xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left px-6 py-4 text-sm text-[#8692A8] font-medium">
                    Feature
                  </th>
                  <th className="px-6 py-4 text-sm text-[#8692A8] text-center font-medium">
                    Detection Tools
                  </th>
                  <th className="px-6 py-4 text-sm text-center font-medium">
                    <span className="forge-gradient-text font-bold">
                      Vibe2Prod
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((f, i) => (
                  <motion.tr
                    key={f.name}
                    initial={{ opacity: 0, x: -20 }}
                    whileInView={{ opacity: 1, x: 0 }}
                    viewport={{ once: true }}
                    transition={{ delay: i * 0.08, duration: 0.4 }}
                    className="border-b border-white/[0.04] last:border-0"
                  >
                    <td className="px-6 py-3.5 text-sm text-[#E8ECF4]">
                      {f.name}
                    </td>
                    <td className="px-6 py-3.5 text-center">
                      {f.others ? (
                        <Check className="size-4 text-[#4E586E] mx-auto" />
                      ) : (
                        <span className="text-[#4E586E]">&mdash;</span>
                      )}
                    </td>
                    <td className="px-6 py-3.5 text-center">
                      <motion.div
                        initial={{ scale: 0 }}
                        whileInView={{ scale: 1 }}
                        viewport={{ once: true }}
                        transition={{
                          delay: 0.3 + i * 0.08,
                          type: "spring",
                          stiffness: 400,
                          damping: 15,
                        }}
                      >
                        <Check className="size-4 text-forge-emerald mx-auto" />
                      </motion.div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </FadeInWhenVisible>
      </div>
    </section>
  );
}
