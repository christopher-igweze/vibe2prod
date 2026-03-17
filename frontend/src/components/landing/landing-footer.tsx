"use client";

import Link from "next/link";
import { SignedOut } from "@clerk/nextjs";
import { FadeInWhenVisible } from "@/components/landing/motion-primitives";
import { SignedInCTA } from "@/components/landing/signed-in-cta";

export function LandingFooter() {
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
