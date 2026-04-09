"use client";

import { Check } from "lucide-react";
import { motion } from "motion/react";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";

export function ComparisonSection() {
  const rows = [
    { name: "Deterministic vulnerability scan", others: true, v2p: true },
    { name: "Runs inside Claude Code (no upload)", others: false, v2p: true },
    { name: "LLM-reasoned severity + context", others: false, v2p: true },
    { name: "Auto-applies the fix via /forge", others: false, v2p: true },
    { name: "Structured false-positive suppression", others: false, v2p: true },
    { name: "Rescans until the repo is clean", others: false, v2p: true },
    { name: "Tuned for Supabase / Lovable / Bolt / v0", others: false, v2p: true },
  ];

  return (
    <section className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)]">
            Why builders pick FORGE
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-12 max-w-2xl mx-auto">
            CodeQL, Snyk, and Semgrep stop at detection and expect you to
            upload a repo. FORGE lives in your editor, explains what to do,
            then{" "}
            <span className="text-forge-emerald font-semibold">
              fixes the code for you.
            </span>
          </p>
        </FadeInWhenVisible>

        <FadeInWhenVisible>
          <div className="forge-glass-card forge-gradient-border rounded-2xl overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-white/[0.06]">
                  <th className="text-left px-6 py-4 text-sm text-[#8692A8] font-medium">
                    Capability
                  </th>
                  <th className="px-6 py-4 text-sm text-[#8692A8] text-center font-medium">
                    Other scanners
                  </th>
                  <th className="px-6 py-4 text-sm text-center font-medium">
                    <span className="forge-gradient-text font-bold">
                      FORGE
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
