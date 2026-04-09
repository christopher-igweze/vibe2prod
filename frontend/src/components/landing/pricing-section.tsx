"use client";

import {
  FadeInWhenVisible,
  TiltCard,
} from "@/components/landing/motion-primitives";

export function PricingSection() {
  const estimates = [
    { size: "Small repo", cost: "~$2", loc: "<5k LOC" },
    { size: "Medium repo", cost: "~$6", loc: "5k-50k LOC" },
    { size: "Large repo", cost: "~$8", loc: "50k+ LOC" },
  ];

  return (
    <section className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-2 font-[family-name:var(--font-heading)]">
            Pay per scan. Or don&rsquo;t.
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-2 max-w-2xl mx-auto">
            These prices are for the managed web UI, and honestly, paying here
            is basically buying me a coffee — the markup keeps the sandbox
            running. For the cheapest scans, grab an{" "}
            <a
              href="https://openrouter.ai/keys"
              target="_blank"
              rel="noopener noreferrer"
              className="text-forge-emerald underline hover:text-forge-emerald-light"
            >
              OpenRouter key
            </a>
            {" "}and switch to BYOK — you pay OpenRouter directly at cost.
          </p>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.12}>
          <p className="text-center text-sm text-[#8692A8] mb-2 max-w-2xl mx-auto">
            <span className="text-forge-emerald font-semibold">No key at all?</span>{" "}
            FORGE still runs the 16 Opengrep rules + deterministic scoring for
            free, forever. You lose the two LLM passes but the static scan is
            yours.
          </p>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.15}>
          <p className="text-center text-sm text-forge-emerald mb-12">
            $15 free balance on signup — no credit card required
          </p>
        </FadeInWhenVisible>
        <div className="grid md:grid-cols-3 gap-6">
          {estimates.map((est, i) => (
            <FadeInWhenVisible key={est.size} delay={i * 0.15}>
              <div style={{ perspective: "800px" }}>
                <TiltCard className="rounded-2xl border p-8 text-center transition-all forge-glass-card">
                  <div className="text-sm text-[#4E586E] mb-2">{est.size}</div>
                  <div className="text-4xl font-bold text-[#E8ECF4] mb-1 font-[family-name:var(--font-heading)]">
                    {est.cost}
                  </div>
                  <div className="text-sm text-[#4E586E]">{est.loc}</div>
                </TiltCard>
              </div>
            </FadeInWhenVisible>
          ))}
        </div>
        <FadeInWhenVisible delay={0.5}>
          <p className="text-center text-xs text-[#4E586E] mt-6">Add funds anytime — $5 minimum deposit</p>
        </FadeInWhenVisible>
      </div>
    </section>
  );
}
