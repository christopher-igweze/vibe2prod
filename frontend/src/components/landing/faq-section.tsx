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
      q: "What types of codebases can Vibe2Prod scan?",
      a: "Any GitHub repository \u2014 public or private. Connect your GitHub account for private repo access. We support all major languages and frameworks.",
    },
    {
      q: "How is this different from CodeRabbit or Snyk?",
      a: "CodeRabbit, Snyk, and Semgrep generate reports. You still do all the work. Vibe2Prod\u2019s FORGE engine auto-remediates critical issues, generates regression tests, validates nothing broke, and hands you a production readiness score. Detection is table stakes \u2014 remediation is the moat.",
    },
    {
      q: 'What does a "scan credit" include?',
      a: "One credit covers a full discovery scan of your repository \u2014 security audit, architecture review, quality analysis, and reliability check \u2014 plus a complete remediation pass with fix validation.",
    },
    {
      q: "How long does a scan take?",
      a: "Typically 2\u201310 minutes depending on repository size. You can leave and check back from your dashboard.",
    },
    {
      q: "Is my code secure?",
      a: "Your code is processed in ephemeral sandboxed environments and never stored after analysis. We use Supabase with Row-Level Security for all data.",
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
