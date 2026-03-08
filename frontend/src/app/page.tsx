import Link from "next/link";
import { SignedOut } from "@clerk/nextjs";
import { Search, Wrench, ShieldCheck } from "lucide-react";
import { SignedInCTA } from "@/components/landing/signed-in-cta";

export const dynamic = "force-dynamic";

function HeroSection() {
  return (
    <section className="relative pt-24 pb-16 text-center overflow-hidden forge-dot-grid">
      {/* Gradient background */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#0B0F19] via-[#0B0F19] to-[#1A1508] pointer-events-none" />
      {/* Soft glow behind heading */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-forge-amber/5 rounded-full blur-3xl pointer-events-none" />

      <div className="relative mx-auto max-w-3xl px-6">
        <div className="inline-flex items-center rounded-full border border-forge-amber/20 bg-forge-amber/10 px-4 py-1.5 text-sm text-forge-amber mb-8 animate-fade-in-up">
          The only AI audit that fixes what it finds
        </div>
        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl animate-fade-in-up-delay-1 font-[family-name:var(--font-heading)]">
          Discover. <span className="text-forge-amber">Fix.</span> Ship.
        </h1>
        <p className="mt-6 text-lg text-[#8692A8] max-w-2xl mx-auto animate-fade-in-up-delay-2">
          Your AI wrote the code. Vibe2Prod audits it, auto-fixes critical
          issues, and validates the result&nbsp;&mdash; 12 specialized agents,
          zero manual triage.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4 animate-fade-in-up-delay-3">
          <SignedOut>
            <Link
              href="/sign-up"
              className="forge-shimmer-cta rounded-lg px-6 py-3 text-base font-semibold transition-colors"
            >
              Join Waiting List
            </Link>
            <Link
              href="/sign-in"
              className="forge-glass forge-glass-hover rounded-lg px-6 py-3 text-base font-semibold text-[#E8ECF4] transition-colors"
            >
              Sign In
            </Link>
          </SignedOut>
          <SignedInCTA variant="hero" />
        </div>
      </div>
    </section>
  );
}

function FeaturesSection() {
  const phases = [
    {
      title: "Discover",
      description:
        "12 AI agents analyze security, architecture, reliability, and quality. Context-aware findings classified by actionability, not just severity.",
      icon: Search,
      delay: "animate-fade-in-up-delay-1",
    },
    {
      title: "Fix",
      description:
        "FORGE\u2019s 3-loop remediation engine auto-fixes critical issues, generates tests, and handles escalation. No manual patching.",
      icon: Wrench,
      delay: "animate-fade-in-up-delay-2",
    },
    {
      title: "Validate",
      description:
        "Integration validator confirms fixes don\u2019t break functionality. Get a Production Readiness Score (0\u2013100) before you ship.",
      icon: ShieldCheck,
      delay: "animate-fade-in-up-delay-3",
    },
  ];

  return (
    <section className="py-20 border-t border-white/[0.06]">
      <div className="mx-auto max-w-5xl px-6">
        <h2 className="text-3xl font-bold text-center mb-12 animate-fade-in-up font-[family-name:var(--font-heading)]">
          The Full Pipeline
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {phases.map((phase) => (
            <div
              key={phase.title}
              className={`forge-glass forge-glass-hover forge-spring-hover rounded-xl p-6 transition-all duration-300 hover:border-forge-amber/40 hover:shadow-[0_0_24px_-6px_rgba(232,145,58,0.15)] ${phase.delay}`}
            >
              <phase.icon className="h-8 w-8 text-forge-amber mb-4" />
              <h3 className="text-lg font-semibold mb-2">{phase.title}</h3>
              <p className="text-sm text-[#8692A8]">{phase.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

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
    <section className="py-20 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="text-3xl font-bold text-center mb-4 font-[family-name:var(--font-heading)]">
          Not Just Severity &mdash;{" "}
          <span className="text-forge-amber">Actionability</span>
        </h2>
        <p className="text-center text-[#8692A8] mb-12 max-w-2xl mx-auto">
          Every finding is classified by what you should actually do about it,
          calibrated to your project&apos;s stage and context.
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          {tiers.map((tier) => (
            <div
              key={tier.label}
              className={`rounded-lg border p-4 ${tier.color}`}
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

function ComparisonSection() {
  return (
    <section className="py-20 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="text-3xl font-bold text-center mb-12 font-[family-name:var(--font-heading)]">
          Why Not Just Another Scanner?
        </h2>
        <div className="grid md:grid-cols-2 gap-6">
          {/* Detection Tools */}
          <div className="forge-glass rounded-xl p-6">
            <h3 className="text-lg font-semibold mb-1">Detection Tools</h3>
            <p className="text-sm text-[#4E586E] mb-4">
              CodeRabbit, Greptile, Snyk
            </p>
            <p className="text-sm text-[#8692A8]">
              Find problems. Generate reports. Leave you to fix everything.
            </p>
          </div>

          {/* Vibe2Prod FORGE */}
          <div className="rounded-xl border border-forge-amber/30 bg-forge-amber/5 p-6">
            <h3 className="text-lg font-semibold text-forge-amber mb-1">
              Vibe2Prod FORGE
            </h3>
            <p className="text-sm text-[#4E586E] mb-4">&nbsp;</p>
            <p className="text-sm text-[#E8ECF4]">
              Find problems. Auto-fix them. Validate the result. Ship
              production-ready code.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

function PricingSection() {
  const packages = [
    { name: "Single", credits: 1, price: "$10", perScan: "$10/scan", highlight: false },
    { name: "Pack", credits: 5, price: "$40", perScan: "$8/scan", highlight: true },
    { name: "Bulk", credits: 15, price: "$99", perScan: "$6.60/scan", highlight: false },
  ];

  return (
    <section className="py-20 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="text-3xl font-bold text-center mb-2 font-[family-name:var(--font-heading)]">Simple Credit Pricing</h2>
        <p className="text-center text-[#8692A8] mb-2">1 credit = 1 scan. Your first scan is free.</p>
        <p className="text-center text-sm text-forge-amber mb-10">1 Free Scan Included With Signup</p>
        <div className="grid md:grid-cols-3 gap-6">
          {packages.map((pkg) => (
            <div key={pkg.name}
              className={`rounded-xl border p-6 text-center ${
                pkg.highlight
                  ? "border-forge-amber/50 bg-forge-amber/5"
                  : "forge-glass"
              }`}
            >
              {pkg.highlight && (
                <div className="text-xs font-semibold text-forge-amber mb-2 uppercase tracking-wider">
                  Most Popular
                </div>
              )}
              <div className="text-lg font-semibold text-[#E8ECF4] mb-1">{pkg.name}</div>
              <div className="text-3xl font-bold text-[#E8ECF4] mb-1">{pkg.price}</div>
              <div className="text-sm text-[#4E586E] mb-3">
                {pkg.credits} credit{pkg.credits > 1 ? "s" : ""} · {pkg.perScan}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function StatsSection() {
  const stats = [
    { value: "12", label: "Specialized AI Agents" },
    { value: "3", label: "Control Loops" },
    { value: "0\u2013100", label: "Production Readiness Score" },
    { value: "Auto-Fix", label: "Not Just Reports" },
  ];

  return (
    <section className="py-20 border-t border-white/[0.06]">
      <div className="mx-auto max-w-4xl px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((stat) => (
            <div key={stat.label}>
              <div className="text-3xl font-bold text-forge-amber">
                {stat.value}
              </div>
              <div className="text-sm text-[#8692A8] mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-white/[0.06] py-8">
      <div className="mx-auto max-w-5xl px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
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
              className="text-sm text-forge-amber hover:text-forge-amber-light transition-colors"
            >
              Join Waiting List
            </Link>
          </SignedOut>
          <SignedInCTA variant="footer" />
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="fixed top-0 w-full forge-glass z-50">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-3">
          <span className="text-lg font-bold tracking-tight font-[family-name:var(--font-heading)]">
            <span className="text-forge-amber">Vibe</span>
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
                className="rounded-lg bg-forge-amber px-4 py-2 text-sm font-semibold text-[#0B0F19] hover:bg-forge-amber-light transition-colors"
              >
                Join Waiting List
              </Link>
            </SignedOut>
            <SignedInCTA variant="nav" />
          </div>
        </div>
      </nav>

      <HeroSection />
      <FeaturesSection />
      <ActionabilitySection />
      <ComparisonSection />
      <PricingSection />
      <StatsSection />
      <Footer />
    </div>
  );
}
