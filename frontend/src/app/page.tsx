"use client";

import { LandingNav } from "@/components/landing/landing-nav";
import { HeroSection } from "@/components/landing/hero-section";
import { SocialProofBar } from "@/components/landing/social-proof-bar";
import { FeaturesSection } from "@/components/landing/features-section";
import { SetupSection } from "@/components/landing/setup-section";
import { HowItWorksSection } from "@/components/landing/how-it-works-section";
import { ActionabilitySection } from "@/components/landing/actionability-section";
import { ComparisonSection } from "@/components/landing/comparison-section";
import { PricingSection } from "@/components/landing/pricing-section";
import { FAQSection } from "@/components/landing/faq-section";
import { LandingFooter } from "@/components/landing/landing-footer";

export const dynamic = "force-dynamic";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <LandingNav />
      <HeroSection />
      <SocialProofBar />
      <FeaturesSection />
      <SetupSection />
      <HowItWorksSection />
      <ActionabilitySection />
      <ComparisonSection />
      <PricingSection />
      <FAQSection />
      <LandingFooter />
    </div>
  );
}
