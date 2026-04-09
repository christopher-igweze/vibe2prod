"use client";

import Link from "next/link";
import { SignedOut } from "@clerk/nextjs";
import { motion } from "motion/react";
import { SignedInCTA } from "@/components/landing/signed-in-cta";

export function LandingNav() {
  return (
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
              Sign Up
            </Link>
          </SignedOut>
          <SignedInCTA variant="nav" />
        </div>
      </div>
    </motion.nav>
  );
}
