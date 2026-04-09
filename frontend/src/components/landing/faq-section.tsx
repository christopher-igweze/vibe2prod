"use client";

import { FadeInWhenVisible } from "@/components/landing/motion-primitives";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export function FAQSection() {
  const faqs = [
    {
      q: "Who is this for?",
      a: "Builders shipping AI-generated apps from Lovable, Bolt, v0, Cursor, Replit, and similar tools \u2014 especially Supabase-backed SaaS projects where the generated code tends to leak service keys, skip RLS, or expose client-writable columns. If you vibe-coded it and now need to put real users on it, this is for you.",
    },
    {
      q: "How is this different from CodeQL, Snyk, or Semgrep?",
      a: "Those tools stop at detection. Vibe2Prod runs deterministic Opengrep scans, layers a 12-agent LLM swarm on top for context-aware review, then auto-applies fixes through three control loops and reruns the scan until clean. It also ships a vulnerability pattern library (VP-001/002/003\u2026) tuned for failure modes specific to AI-generated apps, not generic CWEs.",
    },
    {
      q: "What languages and stacks are supported?",
      a: "Python, TypeScript/JavaScript, and the usual web stack (Next.js, React, FastAPI, Node). Supabase projects get first-class treatment \u2014 RLS policies, service-role-key misuse, and client-writable columns are in the pattern library.",
    },
    {
      q: "How does pricing work?",
      a: "Pay-per-scan, no subscriptions. You get a $15 balance on signup (enough for several scans). Typical costs: ~$2 for small repos, ~$6 for medium, ~$8 for large. Bring your own OpenRouter key (BYOK) and you pay roughly 5x less because you skip the platform markup and settle LLM costs directly with OpenRouter.",
    },
    {
      q: "What do I actually get back?",
      a: "A discovery report with AIVSS-scored findings, a Production Readiness Score (0\u2013100) with per-category breakdowns, and \u2014 when you run remediation \u2014 applied fixes, generated tests, and a re-validated diff. Forgeignore v2 lets you suppress known false positives with structured rules that persist across scans.",
    },
    {
      q: "How long does a scan take?",
      a: "Typically 3\u201315 minutes depending on repository size. Scans run in ephemeral Daytona sandboxes; you can close the tab and check the dashboard later.",
    },
    {
      q: "Is my code secure?",
      a: "Code is cloned into ephemeral sandboxes and torn down after the run. Metadata and reports are stored in Supabase with Row-Level Security. BYOK keys are encrypted at rest and never logged.",
    },
  ];

  return (
    <section className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-3xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl font-bold text-center mb-12 font-[family-name:var(--font-heading)]">
            Questions? Answers.
          </h2>
        </FadeInWhenVisible>
        <Accordion type="single" collapsible className="space-y-3">
          {faqs.map((faq, i) => (
            <FadeInWhenVisible key={i} delay={i * 0.1}>
              <AccordionItem
                value={`faq-${i}`}
                className="forge-glass-card rounded-xl border-none"
              >
                <AccordionTrigger className="px-6 py-4 text-left text-[#E8ECF4] hover:no-underline hover:text-forge-emerald transition-colors">
                  {faq.q}
                </AccordionTrigger>
                <AccordionContent className="px-6 pb-4 text-[#8692A8]">
                  {faq.a}
                </AccordionContent>
              </AccordionItem>
            </FadeInWhenVisible>
          ))}
        </Accordion>
      </div>
    </section>
  );
}
