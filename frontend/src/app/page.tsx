"use client";

import { useRef } from "react";
import Link from "next/link";
import { SignedOut } from "@clerk/nextjs";
import { Search, Wrench, ShieldCheck, Check } from "lucide-react";
import { motion, useScroll, useTransform } from "motion/react";
import { SignedInCTA } from "@/components/landing/signed-in-cta";
import {
  FadeInWhenVisible,
  TiltCard,
  AnimatedCounter,
} from "@/components/landing/motion-primitives";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export const dynamic = "force-dynamic";

/* ─────────────── Hero ─────────────── */

function HeroSection() {
  const ref = useRef(null);
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start start", "end start"],
  });
  const heroY = useTransform(scrollYProgress, [0, 1], [0, -150]);
  const orbY = useTransform(scrollYProgress, [0, 1], [0, 100]);
  const opacity = useTransform(scrollYProgress, [0, 0.8], [1, 0]);

  const words = [
    { text: "Discover.", gradient: false },
    { text: "Fix.", gradient: true },
    { text: "Ship.", gradient: false },
  ];

  return (
    <section
      ref={ref}
      className="relative min-h-[90vh] flex items-center justify-center overflow-hidden"
    >
      {/* Animated gradient mesh background */}
      <div className="absolute inset-0 forge-mesh-bg" />

      {/* Floating orbs — parallax drift downward on scroll */}
      <motion.div style={{ y: orbY }} className="absolute inset-0 pointer-events-none">
        <motion.div
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-forge-emerald/15 rounded-full blur-3xl"
          animate={{ y: [-20, 20, -20], scale: [1, 1.05, 1] }}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-72 h-72 bg-forge-teal/15 rounded-full blur-3xl"
          animate={{ y: [15, -15, 15], scale: [1.05, 1, 1.05] }}
          transition={{ duration: 6, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute top-1/3 right-1/3 w-64 h-64 bg-forge-blue/10 rounded-full blur-3xl"
          animate={{ y: [-10, 25, -10], x: [-10, 10, -10] }}
          transition={{ duration: 10, repeat: Infinity, ease: "easeInOut" }}
        />
      </motion.div>

      {/* Dot grid overlay */}
      <div className="absolute inset-0 forge-dot-grid opacity-40" />

      {/* Hero content — parallax upward + fade on scroll */}
      <motion.div
        style={{ y: heroY, opacity }}
        className="relative mx-auto max-w-4xl px-6 text-center"
      >
        {/* Pill badge */}
        <motion.div
          initial={{ opacity: 0, y: -20, scale: 0.9 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          className="inline-flex items-center rounded-full border border-forge-emerald/20 bg-forge-emerald/10 px-4 py-1.5 text-sm text-forge-emerald mb-8"
        >
          <span className="w-2 h-2 rounded-full bg-forge-emerald mr-2 animate-pulse" />
          The only AI audit that fixes what it finds
        </motion.div>

        {/* Hero headline — staggered word reveal with blur-to-sharp */}
        <h1 className="text-6xl sm:text-7xl lg:text-8xl font-bold tracking-tight font-[family-name:var(--font-heading)] leading-[1.05] overflow-visible">
          {words.map((word, i) => (
            <motion.span
              key={word.text}
              initial={{ opacity: 0, y: 30, filter: "blur(8px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{
                duration: 0.6,
                delay: 0.3 + i * 0.2,
                ease: [0.25, 0.46, 0.45, 0.94],
              }}
              className={word.gradient ? "forge-gradient-text" : "text-foreground"}
              style={{ display: "inline-block", marginRight: "0.3em" }}
            >
              {word.text}
            </motion.span>
          ))}
        </h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className="mt-8 text-lg sm:text-xl text-[#8692A8] max-w-2xl mx-auto leading-relaxed"
        >
          You vibe-coded it. Now ship it without getting hacked. 12 AI agents
          find security holes, architecture debt, and reliability
          gaps&nbsp;&mdash; then fix them automatically.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 1.0 }}
          className="mt-12 flex items-center justify-center gap-4"
        >
          <SignedOut>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Link
                href="/sign-up"
                className="forge-shimmer-cta rounded-xl px-8 py-4 text-lg font-semibold transition-shadow hover:shadow-[0_0_40px_-4px_rgba(52,211,153,0.4)] block"
              >
                Join Waiting List
              </Link>
            </motion.div>
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Link
                href="/sign-in"
                className="forge-glass-card rounded-xl px-8 py-4 text-lg font-semibold text-[#E8ECF4] block"
              >
                Sign In
              </Link>
            </motion.div>
          </SignedOut>
          <SignedInCTA variant="hero" />
        </motion.div>
      </motion.div>

      {/* Bottom gradient fade */}
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-[#0B0F19] to-transparent" />
    </section>
  );
}

/* ─────────────── Social Proof ─────────────── */

function SocialProofBar() {
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

/* ─────────────── Features (3D Tilt) ─────────────── */

function FeaturesSection() {
  const features = [
    {
      title: "Discover",
      subtitle: "4 agents. Full-stack analysis.",
      description:
        "Security auditors, architecture reviewers, quality analysts, and reliability scanners work in parallel. Context-aware findings classified by actionability, not just severity.",
      icon: Search,
    },
    {
      title: "Fix",
      subtitle: "3-loop remediation engine.",
      description:
        "FORGE auto-fixes critical issues with a coder retry loop, escalation loop, and replan loop. Generates tests. Handles edge cases. No manual patching.",
      icon: Wrench,
    },
    {
      title: "Validate",
      subtitle: "Production readiness, quantified.",
      description:
        "Integration validator confirms fixes don\u2019t break functionality. Get a Production Readiness Score (0\u2013100) with category breakdowns before you ship.",
      icon: ShieldCheck,
    },
  ];

  return (
    <section className="py-24">
      <div className="mx-auto max-w-6xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-4 font-[family-name:var(--font-heading)]">
            The Full Pipeline
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-16 max-w-2xl mx-auto">
            Other tools hand you a PDF of problems. We hand you
            production-ready code.
          </p>
        </FadeInWhenVisible>

        <div className="space-y-16 md:space-y-24">
          {features.map((feature, i) => (
            <FadeInWhenVisible
              key={feature.title}
              delay={i * 0.15}
              className={`flex flex-col ${
                i % 2 === 0 ? "md:flex-row" : "md:flex-row-reverse"
              } items-center gap-8 md:gap-16`}
            >
              {/* Icon block with 3D tilt */}
              <div
                className="flex-1 flex items-center justify-center"
                style={{ perspective: "800px" }}
              >
                <TiltCard className="relative w-52 h-52 sm:w-64 sm:h-64 rounded-3xl forge-glass-card forge-gradient-border flex items-center justify-center">
                  <feature.icon
                    className="size-16 sm:size-20 text-forge-emerald"
                    strokeWidth={1.5}
                  />
                  {/* Floating number badge — pops out in 3D */}
                  <div
                    className="absolute -top-3 -left-3 w-10 h-10 rounded-full bg-forge-emerald text-[#0B0F19] flex items-center justify-center font-bold text-lg font-[family-name:var(--font-heading)]"
                    style={{ transform: "translateZ(30px)" }}
                  >
                    {i + 1}
                  </div>
                  {/* Inner glow on hover */}
                  <div className="absolute inset-0 rounded-3xl bg-gradient-to-br from-forge-emerald/10 to-transparent opacity-0 hover:opacity-100 transition-opacity duration-500" />
                </TiltCard>
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
            </FadeInWhenVisible>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─────────────── How It Works ─────────────── */

function HowItWorksSection() {
  const containerRef = useRef(null);
  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ["start 0.8", "end 0.6"],
  });
  const lineHeight = useTransform(scrollYProgress, [0, 1], ["0%", "100%"]);

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
    <section
      ref={containerRef}
      className="py-24 border-t border-white/[0.06]"
    >
      <div className="mx-auto max-w-5xl px-6">
        <FadeInWhenVisible>
          <h2 className="text-4xl sm:text-5xl font-bold text-center mb-16 font-[family-name:var(--font-heading)]">
            How It Works
          </h2>
        </FadeInWhenVisible>

        <div className="relative">
          {/* Animated connecting line — draws on scroll */}
          <div className="absolute left-8 top-0 bottom-0 w-px bg-white/[0.06] hidden md:block">
            <motion.div
              className="w-full bg-gradient-to-b from-forge-emerald to-forge-teal"
              style={{ height: lineHeight }}
            />
          </div>

          <div className="space-y-12">
            {steps.map((step, i) => (
              <FadeInWhenVisible key={step.num} delay={i * 0.15}>
                <div className="flex items-start gap-8">
                  <motion.div
                    className="shrink-0 w-16 h-16 rounded-2xl bg-forge-emerald/10 border border-forge-emerald/20 flex items-center justify-center font-[family-name:var(--font-heading)] text-forge-emerald font-bold text-xl relative z-10"
                    whileHover={{
                      scale: 1.1,
                      borderColor: "rgba(52,211,153,0.5)",
                    }}
                    transition={{
                      type: "spring",
                      stiffness: 300,
                      damping: 20,
                    }}
                  >
                    {step.num}
                  </motion.div>
                  <div className="pt-2">
                    <h3 className="text-xl font-bold mb-2 font-[family-name:var(--font-heading)]">
                      {step.title}
                    </h3>
                    <p className="text-[#8692A8]">{step.desc}</p>
                  </div>
                </div>
              </FadeInWhenVisible>
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

/* ─────────────── Comparison Table ─────────────── */

function ComparisonSection() {
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

/* ─────────────── Pricing ─────────────── */

function PricingSection() {
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
            Pay Only For What You Use
          </h2>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.1}>
          <p className="text-center text-[#8692A8] mb-2">
            No subscriptions, no wasted credits. You only pay for scans you run.
          </p>
        </FadeInWhenVisible>
        <FadeInWhenVisible delay={0.15}>
          <p className="text-center text-sm text-forge-emerald mb-12">
            $15 Free Balance Included With Signup
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

/* ─────────────── FAQ ─────────────── */

function FAQSection() {
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

/* ─────────────── Footer ─────────────── */

function Footer() {
  return (
    <FadeInWhenVisible>
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
    </FadeInWhenVisible>
  );
}

/* ─────────────── Main Page ─────────────── */

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav — visible frosted glass + slide-down entrance */}
      <motion.nav
        className="fixed top-0 w-full forge-glass-nav z-50"
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        transition={{ duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
      >
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
      </motion.nav>

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
