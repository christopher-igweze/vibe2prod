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
      a: "Builders shipping AI-generated apps from Lovable, Bolt, v0, Cursor, Replit, and similar tools — especially Supabase-backed SaaS projects where the generated code tends to leak service keys, skip RLS, or expose client-writable columns. If you vibe-coded it and now need to put real users on it, this is for you.",
    },
    {
      q: "How do I install FORGE into Claude Code?",
      a: "Two commands: `pip install vibe2prod` then `vibe2prod setup`. The interactive wizard detects Claude Code, asks for your OpenRouter key, registers the FORGE MCP server (forge_scan, forge_status, forge_config, forge_health) and copies the /forge and /forgeignore slash skills into ~/.claude/commands/. After that, running `/forge` inside any repo drives the full audit → triage → fix → rescan loop. For CI or scripted installs use `vibe2prod setup --no-interactive --api-key sk-or-…` instead.",
    },
    {
      q: "How is this different from CodeQL, Snyk, or Semgrep?",
      a: "Those tools detect and stop. FORGE runs 16 deterministic Opengrep rules, then layers two targeted LLM passes (Codebase Analyst + Security Auditor) on top for context-aware review, then hands the findings to Claude inside your editor to actually apply the fixes. Because it lives as an MCP server in Claude Code, your repo never has to be uploaded anywhere, and the fix loop is auditable line by line.",
    },
    {
      q: "What does an actual scan look like under the hood?",
      a: "16 Opengrep rules run first at zero LLM cost (hardcoded secrets, SQL injection, XSS, path traversal, command injection, SSRF, auth bypass, CORS, insecure crypto, debug mode, verbose errors, error handling, silent exceptions, N+1, sync-in-async). Then a Codebase Analyst (Minimax M2.5) maps your architecture, and a Security Auditor (Claude Haiku 4.5) reasons over the merged findings for context and severity. Results are deduped, fingerprinted, and given a Production Readiness Score between 0 and 100.",
    },
    {
      q: "What languages and stacks are supported?",
      a: "Python, TypeScript/JavaScript, and the usual web stack (Next.js, React, FastAPI, Node). Supabase projects get first-class treatment — RLS policies, service-role-key misuse, and client-writable columns are part of the rule set.",
    },
    {
      q: "How does pricing work?",
      a: "Two paths. (1) MCP in Claude Code: you bring your own OpenRouter key and pay OpenRouter directly for the two LLM passes — typically pennies per scan. (2) The managed web UI at vibe2prod.net: pay-per-scan with a $15 signup credit, ~$2 small repos, ~$6 medium, ~$8 large. No subscriptions either way, and you can switch on BYOK inside the web UI too.",
    },
    {
      q: "How long does a scan take?",
      a: "Typically 3–15 minutes depending on repo size. Via the MCP server it runs against your local working tree; via the web UI it runs in an ephemeral Daytona sandbox that's torn down after the run.",
    },
    {
      q: "Is my code secure?",
      a: "The MCP path keeps your code entirely on your machine — Claude Code reads files directly. The managed web path clones into an ephemeral sandbox that's destroyed after the run. Metadata and reports are stored in Supabase behind Row-Level Security, and BYOK keys are encrypted at rest and never logged.",
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
