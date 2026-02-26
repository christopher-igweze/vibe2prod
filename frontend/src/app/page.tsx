import { Waitlist } from "@clerk/nextjs";
import Link from "next/link";

export const dynamic = "force-dynamic";

function HeroSection() {
  return (
    <section className="pt-24 pb-16 text-center">
      <div className="mx-auto max-w-3xl px-6">
        <div className="inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-1.5 text-sm text-emerald-400 mb-8">
          Free for early adopters — 5 scans included
        </div>
        <h1 className="text-5xl font-bold tracking-tight sm:text-6xl">
          Ship AI Code{" "}
          <span className="text-emerald-400">With Confidence</span>
        </h1>
        <p className="mt-6 text-lg text-neutral-400 max-w-2xl mx-auto">
          Your AI wrote the code. Vibe2Prod tells you if it&apos;s ready for production.
          Get actionable security, reliability, and scalability findings —
          prioritized for your project stage.
        </p>
      </div>
    </section>
  );
}

function WaitlistSection() {
  return (
    <section id="waitlist" className="py-12">
      <div className="mx-auto max-w-md px-6">
        <Waitlist
          appearance={{
            elements: {
              rootBox: "mx-auto w-full",
              card: "bg-neutral-900 border border-neutral-800 shadow-2xl shadow-emerald-500/5",
              headerTitle: "text-neutral-100",
              headerSubtitle: "text-neutral-400",
              formFieldInput:
                "bg-neutral-800 border-neutral-700 text-neutral-100 placeholder:text-neutral-500",
              formButtonPrimary:
                "bg-emerald-500 hover:bg-emerald-400 text-neutral-950 font-semibold",
              footerActionLink: "text-emerald-400 hover:text-emerald-300",
            },
          }}
        />
      </div>
    </section>
  );
}

function FeaturesSection() {
  const features = [
    {
      title: "Paste. Scan. Ship.",
      description:
        "Drop a GitHub URL, fill in your project context, and get a full audit in minutes. No setup, no CI integration required.",
      icon: "🔍",
    },
    {
      title: "Context-Aware Prioritization",
      description:
        "Findings are classified as Must Fix, Should Fix, Consider, or Informational — calibrated to your project stage (MVP vs Enterprise).",
      icon: "🎯",
    },
    {
      title: "Downloadable Reports",
      description:
        "Get your audit as a rendered web report, downloadable Markdown for your coding agent, or a PDF for stakeholders.",
      icon: "📊",
    },
  ];

  return (
    <section className="py-20 border-t border-neutral-800">
      <div className="mx-auto max-w-5xl px-6">
        <h2 className="text-3xl font-bold text-center mb-12">
          How It Works
        </h2>
        <div className="grid md:grid-cols-3 gap-8">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6"
            >
              <div className="text-3xl mb-4">{feature.icon}</div>
              <h3 className="text-lg font-semibold mb-2">{feature.title}</h3>
              <p className="text-sm text-neutral-400">{feature.description}</p>
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
      description: "Exploitable vulnerabilities — fix before shipping",
    },
    {
      label: "Should Fix",
      color: "text-orange-400 bg-orange-500/10 border-orange-500/20",
      description: "Real issues — prioritize this sprint",
    },
    {
      label: "Consider",
      color: "text-yellow-400 bg-yellow-500/10 border-yellow-500/20",
      description: "Valid observations — address when convenient",
    },
    {
      label: "Informational",
      color: "text-blue-400 bg-blue-500/10 border-blue-500/20",
      description: "Noted for awareness — no action needed",
    },
  ];

  return (
    <section className="py-20 border-t border-neutral-800">
      <div className="mx-auto max-w-4xl px-6">
        <h2 className="text-3xl font-bold text-center mb-4">
          Not Just Severity — <span className="text-emerald-400">Actionability</span>
        </h2>
        <p className="text-center text-neutral-400 mb-12 max-w-2xl mx-auto">
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

function StatsSection() {
  const stats = [
    { value: "15+", label: "Static Checks" },
    { value: "3", label: "Vulnerability Patterns" },
    { value: "< 2 min", label: "Average Scan Time" },
    { value: "4", label: "Actionability Tiers" },
  ];

  return (
    <section className="py-20 border-t border-neutral-800">
      <div className="mx-auto max-w-4xl px-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 text-center">
          {stats.map((stat) => (
            <div key={stat.label}>
              <div className="text-3xl font-bold text-emerald-400">
                {stat.value}
              </div>
              <div className="text-sm text-neutral-400 mt-1">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-neutral-800 py-8">
      <div className="mx-auto max-w-5xl px-6 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="text-sm text-neutral-500">
          © {new Date().getFullYear()} Vibe2Prod. All rights reserved.
        </div>
        <div className="flex items-center gap-6">
          <Link
            href="/sign-in"
            className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="#waitlist"
            className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            Join Waitlist
          </Link>
        </div>
      </div>
    </footer>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-neutral-950">
      {/* Nav */}
      <nav className="fixed top-0 w-full border-b border-neutral-800 bg-neutral-950/80 backdrop-blur-sm z-50">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-3">
          <span className="text-lg font-bold tracking-tight">
            <span className="text-emerald-400">Vibe</span>
            <span className="text-neutral-100">2Prod</span>
          </span>
          <div className="flex items-center gap-4">
            <Link
              href="/sign-in"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              Sign In
            </Link>
            <Link
              href="#waitlist"
              className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-neutral-950 hover:bg-emerald-400 transition-colors"
            >
              Get Early Access
            </Link>
          </div>
        </div>
      </nav>

      <HeroSection />
      <WaitlistSection />
      <FeaturesSection />
      <ActionabilitySection />
      <StatsSection />
      <Footer />
    </div>
  );
}
