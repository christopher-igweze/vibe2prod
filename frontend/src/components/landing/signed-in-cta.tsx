"use client"

import Link from "next/link"
import { useAuth } from "@clerk/nextjs"
import { Loader2 } from "lucide-react"
import { useUserRole } from "@/hooks/use-user-role"

// Two variants: "hero" (large buttons) and "nav" (small buttons)
export function SignedInCTA({ variant = "hero" }: { variant?: "hero" | "nav" | "footer" }) {
  const { isSignedIn, isLoaded } = useAuth()
  const { role, loading } = useUserRole()

  if (!isLoaded || loading) {
    return <Loader2 className="size-4 animate-spin text-[#4E586E]" />
  }

  // Not signed in — render nothing (SignedOut block handles this)
  if (!isSignedIn) {
    return null
  }

  // Waitlisted user — show waitlist message
  if (role === "user") {
    if (variant === "hero") {
      return (
        <div className="text-center space-y-3">
          <p className="text-amber-400 font-medium">You&apos;re on the waitlist!</p>
          <p className="text-[#8692A8] text-sm">We&apos;re rolling out access in waves.</p>
          <p className="text-[#4E586E] text-sm">
            Follow for updates:{" "}
            <a href="https://linkedin.com/in/christopher-igweze" target="_blank" rel="noopener noreferrer"
              className="text-forge-amber hover:text-forge-amber-light underline">
              LinkedIn
            </a>
          </p>
        </div>
      )
    }
    // nav/footer variant — just show a compact status
    return (
      <span className="text-sm text-amber-400">Waitlisted</span>
    )
  }

  // Active user — show dashboard link
  if (variant === "hero") {
    return (
      <Link href="/dashboard"
        className="rounded-lg bg-forge-amber px-6 py-3 text-base font-semibold text-[#0B0F19] hover:bg-forge-amber-light transition-colors">
        Go to Dashboard
      </Link>
    )
  }
  if (variant === "nav") {
    return (
      <Link href="/dashboard"
        className="rounded-lg bg-forge-amber px-4 py-2 text-sm font-semibold text-[#0B0F19] hover:bg-forge-amber-light transition-colors">
        Dashboard
      </Link>
    )
  }
  // footer
  return (
    <Link href="/dashboard" className="text-sm text-forge-amber hover:text-forge-amber-light transition-colors">
      Dashboard
    </Link>
  )
}
