"use client";

import { useEffect } from "react";
import Link from "next/link";
import { SignedOut } from "@clerk/nextjs";
import { Search, Wrench, ShieldCheck, Check } from "lucide-react";
import { SignedInCTA } from "@/components/landing/signed-in-cta";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export const dynamic = "force-dynamic";

function useScrollReveal() {
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -60px 0px" }
    );

    document.querySelectorAll(".forge-scroll-reveal").forEach((el) => {
      observer.observe(el);
    });

    return () => observer.disconnect();
  }, []);
}

/* ─────────────── Hero ─────────────── */

function HeroSection() {
  return (
    <section className="relative min-h-[90vh] flex items-center justify-center overflow-hidden">
      {/* Animated gradient mesh background */}
      <div className="absolute inset-0 forge-mesh-bg" />

      {/* Floating orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-forge-emerald/5 rounded-full blur-3xl forge-float-slow pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-forge-teal/5 rounded-full blur-3xl forge-float-medium pointer-events-none" />
      <div
        className="absolute top-1/3 right-1/3 w-64 h-64 bg-forge-blue/[0.03] rounded-full blur-3xl forge-float-slow pointer-events-none"
        style={{ animationDelay: "-3s" }}
      />

      {/* Dot grid overlay */}
      <div className="absolute inset-0 forge-dot-grid opacity-40" />

      <div className="relative mx-auto max-w-4xl px-6 text-center">
        {/* Pill badge */}
        <div className="inline-flex items-center rounded-full border border-forge-emerald/20 bg-forge-emerald/10 px-4 py-1.5 text-sm text-forge-emerald mb-8 animate-fade-in-up">
          <span className="w-2 h-2 rounded-full bg-forge-emerald mr-2 animate-pulse" />
          The only AI audit that fixes what it finds
        </div>

        {/* Hero headline */}
        <h1 className="text-6xl sm:text-7xl lg:text-8xl font-bold tracking-tight animate-fade-in-up-delay-1 font-[family-name:var(--font-heading)] leading-[0.95]">
          <span className="text-foreground">Discover.</span>{" "}
          <span className="forge-gradient-text">Fix.</span>{" "}
          <span className="text-foreground">Ship.</span>
        </h1>

        {/* Subheadline */}
        <p className="mt-8 text-lg sm:text-xl text-[#8692A8] max-w-2xl mx-auto animate-fade-in-up-delay-2 leading-relaxed">
          Your AI wrote the code. Vibe2Prod audits it, auto-fixes critical
          issues, and validates the result&nbsp;&mdash; 12 specialized agents,
          zero manual triage.
        </p>

        {/* CTA buttons */}
        <div className="mt-12 flex items-center justify-center gap-4 animate-fade-in-up-delay-3">
          <SignedOut>
            <Link
              href="/sign-up"
              className="forge-shimmer-cta forge-pulse-glow rounded-xl px-8 py-4 text-lg font-semibold transition-all"
            >
              Join Waiting List
            </Link>
            <Link
              href="/sign-in"
              className="forge-glass forge-glass-hover rounded-xl px-8 py-4 text-lg font-semibold text-[#E8ECF4] transition-all"
            >
              Sign In
            </Link>
          </SignedOut>
          <SignedInCTA variant="hero" />
        </div>
      </div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0B0F19] to-transparent" />
    </section>
  );
}

/* ─────────────── Social Proof ─────────────── */

function SocialProofBar() {
  const stats = [
    { value: "12", label: "AI Agents" },
    { value: "3", label: "Control Loops" },
    { value: "0\u2013100", label: "Readiness Score" },
    { value: "Auto", label: "Fix & Validate" },
  ];

  return (
    <section className="py-16 border-y border-white/[0.06]">
      <div className="mx-auto max-w-5xl px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((stat) => (
            <div key={stat.label} className="forge-scroll-reveal">
              <div className="text-4xl sm:text-5xl font-bold forge-gradient-text font-[family-name:var(--font-heading)]">
                {stat.value}
              </div>
              <div className="text-sm text-[#8692A8] mt-2">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────── Features (Asymmetric) ─────────────── */

function FeaturesSection() {
  const features = [
    {
      title: "Discover",
      subtitle: "12 agents. Full-stack analysis.",
      description:
        "Security auditors, architecture reviewers, quality analysts, and reliability scanners work in parallel. Context-aware findings classified by actionability, not just severity.",
      icon: Search,
      gradient: "from-emerald-500/20 to-teal-500/10",
    },
    {
      title: "Fix",
      subtitle: "3-loop remediation engine.",
      description:
        "FORGE auto-fixes critical issues with a coder retry loop, escalation loop, and replan loop. Generates tests. Handles edge cases. No manual patching.",
      icon: Wrench,
      gradient: "from-teal-500/20 to-blue-500/10",
    },
    {
      title: "Validate",
      subtitle: "Production readiness, quantified.",
      description:
        "Integration validator confirms fixes don\u2019t break functionality. Get a Production Readiness Score (0\u2013100) with category breakdowns before you ship.",
      icon: ShieldCheck,
      gradient: "from-blue-500/20 to-emerald-500/10",
    },
  ];

  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)] forge-scroll-reveal">
          The Full Pipeline
        </h2>
        <p className="text-center text-[#8692A8] mb-16 max-w-2xl mx-auto forge-scroll-reveal">
          Three phases. End-to-end. From raw AI code to production-ready.
        </p>

        <div className="space-y-16 md:space-y-24">
          {features.map((feature, i) => (
            <div
              key={feature.title}
              className={`forge-scroll-reveal flex flex-col ${
                i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              } items-center gap-8 md:gap-16`}
            >
              {/* Icon block */}
              <div className="flex-1 flex items-center justify-center">
                <div
                  className={`relative w-52 h-52 sm:w-64 sm:h-64 rounded-3xl bg-gradient-to-br ${feature.gradient} flex items-center justify-center forge-gradient-border`}
                >
                  <feature.icon
                    className="size-16 sm:size-20 text-forge-emerald"
                    strokeWidth={1.5}
                  />
                  <div className="absolute -top-3 -left-3 w-10 h-10 rounded-full bg-forge-emerald text-[#0B0F19] flex items-center justify-center font-bold text-lg font-[family-name:var(--font-heading)]">
                    {i + 1}
                  </div>
                </div>
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
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────── How It Works ─────────────── */

function HowItWorksSection() {
  const steps = [
    {
      num: "01",
      title: "Paste your repo URL",
      desc: "Public or private GitHub repos. Connect GitHub for private access.",
    },
    {
      num: "02",
      title: "FORGE analyzes",
      desc: "12 specialized agents scan security, architecture, quality, and reliability.",
    },
    {
      num: "03",
      title: "Review findings",
      desc: "Actionable findings classified by what to do, not just severity.",
    },
    {
      num: "04",
      title: "Auto-fix & validate",
      desc: "FORGE remediates critical issues, generates tests, validates results.",
    },
  ];

  return (
    <section className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-5xl px-6">
        <h2 className="text-4xl sm:text-5xl font-bold text-center mb-16 font-[family-name:var(--font-heading)] forge-scroll-reveal">
          How It Works
        </h2>

        <div className="relative">
          {/* Vertical connecting line */}
          <div className="absolute left-8 top-0 bottom-0 w-px bg-gradient-to-b from-forge-emerald/40 via-forge-teal/20 to-transparent hidden md:block" />

          <div className="space-y-12">
            {steps.map((step, i) => (
              <div
                key={step.num}
                className="forge-scroll-reveal flex items-start gap-8"
                style={{ transitionDelay: `${i * 100}ms` }}
              >
                <div className="shrink-0 w-16 h-16 rounded-2xl bg-forge-emerald/10 border border-forge-emerald/20 flex items-center justify-center font-[family-name:var(--font-heading)] text-forge-emerald font-bold text-xl relative z-10">
                  {step.num}
                </div>
                <div className="pt-2">
                  <h3 className="text-xl font-bold mb-2 font-[family-name:var(--font-heading)]">
                    {step.title}
                  </h3>
                  <p className="text-[#8692A8]">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─────────────── Actionability ─────────────── */

function ActionabilitySection() {
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
        <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)] forge-scroll-reveal">
          Not Just Severity &mdash;{" "}
          <span className="forge-gradient-text">Actionability</span>
        </h2>
        <p className="text-center text-[#8692A8] mb-12 max-w-2xl mx-auto forge-scroll-reveal">
          Every finding is classified by what you should actually do about it,
          calibrated to your project&apos;s stage and context.
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          {tiers.map((tier) => (
            <div
              key={tier.label}
              className={`forge-scroll-reveal rounded-xl border p-5 ${tier.color}`}
            >
              <div className="font-semibold mb-1">{tier.label}</div>
              <div className="text-sm opacity-80">{tier.description}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────── Comparison Table ─────────────── */

function ComparisonSection() {
  const features = [
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
        <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)] forge-scroll-reveal">
          Not Just Another Scanner
        </h2>
        <p className="text-center text-[#8692A8] mb-12 forge-scroll-reveal">
          Everyone else tells you what&apos;s wrong.{" "}
          <span className="text-forge-emerald font-semibold">We fix it.</span>
        </p>

        <div className="forge-glass forge-gradient-border rounded-2xl overflow-hidden forge-scroll-reveal">
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
              {features.map((f) => (
                <tr
                  key={f.name}
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
                    <Check className="size-4 text-forge-emerald mx-auto" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

/* ─────────────── Pricing ─────────────── */

function PricingSection() {
  const packages = [
    {
      name: "Single",
      credits: 1,
      price: "$10",
      perScan: "$10/scan",
      highlight: false,
    },
    {
      name: "Pack",
      credits: 5,
      price: "$40",
      perScan: "$8/scan",
      highlight: true,
    },
    {
      name: "Bulk",
      credits: 15,
      price: "$99",
      perScan: "$6.60/scan",
      highlight: false,
    },
  ];

  return (
    <section className="py-24 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="text-4xl sm:text-5xl font-bold text-center mb-2 font-[family-name:var(--font-heading)] forge-scroll-reveal">
          Simple Credit Pricing
        </h2>
        <p className="text-center text-[#8692A8] mb-2 forge-scroll-reveal">
          1 credit = 1 scan. Your first scan is free.
        </p>
        <p className="text-center text-sm text-forge-emerald mb-12 forge-scroll-reveal">
          1 Free Scan Included With Signup
        </p>
        <div className="grid md:grid-cols-3 gap-6">
          {packages.map((pkg) => (
            <div
              key={pkg.name}
              className={`forge-scroll-reveal rounded-2xl border p-8 text-center transition-all ${
                pkg.highlight
                  ? "border-forge-emerald/30 bg-forge-emerald/5 forge-gradient-border forge-glow-emerald-sm"
                  : "forge-glass"
              }`}
            >
              {pkg.highlight && (
                <div className="text-xs font-semibold text-forge-emerald mb-3 uppercase tracking-wider">
                  Most Popular
                </div>
              )}
              <div className="text-lg font-semibold text-[#E8ECF4] mb-1">
                {pkg.name}
              </div>
              <div className="text-4xl font-bold text-[#E8ECF4] mb-1 font-[family-name:var(--font-heading)]">
                {pkg.price}
              </div>
              <div className="text-sm text-[#4E586E]">
                {pkg.credits} credit{pkg.credits > 1 ? "s" : ""} ·{" "}
                {pkg.perScan}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────── FAQ ─────────────── */

function FAQSection() {
  const faqs = [
    {
      q: "What types of codebases can Vibe2Prod scan?",
      a: "Any GitHub repository \u2014 public or private. Connect your GitHub account for private repo access. We support all major languages and frameworks.",
    },
    {
      q: "How is this different from CodeRabbit or Snyk?",
      a: "Those tools find problems. We find AND fix them. Our 12-agent FORGE engine auto-remediates critical issues, generates tests, and validates that fixes don\u2019t break anything.",
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
        <h2 className="text-4xl font-bold text-center mb-12 font-[family-name:var(--font-heading)] forge-scroll-reveal">
          Questions? Answers.
        </h2>
        <Accordion type="single" collapsible className="space-y-3">
          {faqs.map((faq, i) => (
            <AccordionItem
              key={i}
              value={`faq-${i}`}
              className="forge-glass rounded-xl border-none forge-scroll-reveal"
            >
              <AccordionTrigger className="px-6 py-4 text-left text-[#E8ECF4] hover:no-underline hover:text-forge-emerald transition-colors">
                {faq.q}
              </AccordionTrigger>
              <AccordionContent className="px-6 pb-4 text-[#8692A8]">
                {faq.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </section>
  );
}

/* ─────────────── Footer ─────────────── */

function Footer() {
  return (
    <footer className="border-t border-white/[0.06] py-12">
      <div className="mx-auto max-w-5xl px-6">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          {/* Brand */}
          <div>
            <span className="text-lg font-bold tracking-tight font-[family-name:var(--font-heading)]">
              <span className="forge-gradient-text">Vibe</span>
              <span className="text-foreground">2Prod</span>
            </span>
            <p className="text-sm text-[#4E586E] mt-2">
              Ship AI code with confidence.
            </p>
          </div>

          {/* Product links */}
          <div>
            <h4 className="text-sm font-semibold text-[#8692A8] mb-3">
              Product
            </h4>
            <div className="space-y-2">
              <Link
                href="/sign-up"
                className="text-sm text-[#4E586E] hover:text-forge-emerald transition-colors block"
              >
                Join Waiting List
              </Link>
              <Link
                href="/sign-in"
                className="text-sm text-[#4E586E] hover:text-forge-emerald transition-colors block"
              >
                Sign In
              </Link>
            </div>
          </div>

          {/* Social */}
          <div>
            <h4 className="text-sm font-semibold text-[#8692A8] mb-3">
              Connect
            </h4>
            <div className="space-y-2">
              <a
                href="https://linkedin.com/in/christopher-igweze"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-[#4E586E] hover:text-forge-emerald transition-colors block"
              >
                LinkedIn
              </a>
            </div>
          </div>
        </div>

        <div className="border-t border-white/[0.06] pt-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="text-sm text-[#4E586E]">
            &copy; {new Date().getFullYear()} Vibe2Prod. All rights reserved.
          </div>
          <div className="flex items-center gap-6">
            <SignedOut>
              <Link
                href="/sign-in"
                className="text-sm text-[#8692A8] hover:text-foreground transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/sign-up"
                className="text-sm text-forge-emerald hover:text-forge-emerald-light transition-colors"
              >
                Join Waiting List
              </Link>
            </SignedOut>
            <SignedInCTA variant="footer" />
          </div>
        </div>
      </div>
    </footer>
  );
}

/* ─────────────── Main Page ─────────────── */

export default function LandingPage() {
  useScrollReveal();

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="fixed top-0 w-full forge-glass z-50">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-3">
          <span className="text-lg font-bold tracking-tight font-[family-name:var(--font-heading)]">
            <span className="forge-gradient-text">Vibe</span>
            <span className="text-foreground">2Prod</span>
          </span>
          <div className="flex items-center gap-4">
            <SignedOut>
              <Link
                href="/sign-in"
                className="text-sm text-[#8692A8] hover:text-foreground transition-colors"
              >
                Sign In
              </Link>
              <Link
                href="/sign-up"
                className="rounded-xl bg-forge-emerald px-4 py-2 text-sm font-semibold text-[#0B0F19] hover:bg-forge-emerald-light transition-colors"
              >
                Join Waiting List
              </Link>
            </SignedOut>
            <SignedInCTA variant="nav" />
          </div>
        </div>
      </nav>

      <HeroSection />
      <SocialProofBar />
      <FeaturesSection />
      <HowItWorksSection />
      <ActionabilitySection />
      <ComparisonSection />
      <PricingSection />
      <FAQSection />
      <Footer />
    </div>
  );
}
