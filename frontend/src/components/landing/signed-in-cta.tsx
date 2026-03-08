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
    return <Loader2 className="size-4 animate-spin text-neutral-500" />
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
          <p className="text-neutral-400 text-sm">We&apos;re rolling out access in waves.</p>
          <p className="text-neutral-500 text-sm">
            Follow for updates:{" "}
            <a href="https://linkedin.com/in/christopher-igweze" target="_blank" rel="noopener noreferrer"
              className="text-emerald-400 hover:text-emerald-300 underline">
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
        className="rounded-lg bg-emerald-500 px-6 py-3 text-base font-semibold text-neutral-950 hover:bg-emerald-400 transition-colors">
        Go to Dashboard
      </Link>
    )
  }
  if (variant === "nav") {
    return (
      <Link href="/dashboard"
        className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-neutral-950 hover:bg-emerald-400 transition-colors">
        Dashboard
      </Link>
    )
  }
  // footer
  return (
    <Link href="/dashboard" className="text-sm text-emerald-400 hover:text-emerald-300 transition-colors">
      Dashboard
    </Link>
  )
}
