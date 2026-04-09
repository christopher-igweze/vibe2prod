"use client"

import Link from "next/link"
import { useAuth } from "@clerk/nextjs"
import { Loader2 } from "lucide-react"

// Two variants: "hero" (large buttons) and "nav" (small buttons)
export function SignedInCTA({ variant = "hero" }: { variant?: "hero" | "nav" | "footer" }) {
  const { isSignedIn, isLoaded } = useAuth()

  if (!isLoaded) {
    return <Loader2 className="size-4 animate-spin text-[#4E586E]" />
  }

  // Not signed in — render nothing (SignedOut block handles this)
  if (!isSignedIn) {
    return null
  }

  // Signed-in user — show dashboard link
  if (variant === "hero") {
    return (
      <Link href="/dashboard"
        className="rounded-lg bg-forge-emerald px-6 py-3 text-base font-semibold text-[#0B0F19] hover:bg-forge-emerald-light transition-colors">
        Go to Dashboard
      </Link>
    )
  }
  if (variant === "nav") {
    return (
      <Link href="/dashboard"
        className="rounded-lg bg-forge-emerald px-4 py-2 text-sm font-semibold text-[#0B0F19] hover:bg-forge-emerald-light transition-colors">
        Dashboard
      </Link>
    )
  }
  // footer
  return (
    <Link href="/dashboard" className="text-sm text-forge-emerald hover:text-forge-emerald-light transition-colors">
      Dashboard
    </Link>
  )
}
