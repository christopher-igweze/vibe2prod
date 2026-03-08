"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { UserButton } from "@clerk/nextjs"
import Link from "next/link"
import { Loader2 } from "lucide-react"
import { useUserRole } from "@/hooks/use-user-role"

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { role, profile, loading } = useUserRole()

  useEffect(() => {
    if (loading) return
    if (role === "user") {
      router.replace("/")
      return
    }
    if (profile && !profile.onboarding_complete && pathname !== "/onboarding") {
      router.replace("/onboarding")
    }
  }, [role, profile, loading, pathname, router])

  if (loading) {
    return (
      <div className="min-h-screen bg-neutral-950 flex items-center justify-center">
        <Loader2 className="size-6 animate-spin text-neutral-500" />
      </div>
    )
  }

  // Onboarding or waitlisted users: no nav, just the page content
  if (role === "user" || (profile && !profile.onboarding_complete)) {
    return (
      <div className="min-h-screen bg-neutral-950">
        <div className="mx-auto max-w-6xl px-6 py-3">
          <Link href="/" className="text-lg font-bold tracking-tight">
            <span className="text-emerald-400">Vibe</span>
            <span className="text-neutral-100">2Prod</span>
          </Link>
        </div>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-neutral-950">
      <nav className="border-b border-neutral-800 bg-neutral-950/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-3">
          <Link href="/" className="text-lg font-bold tracking-tight">
            <span className="text-emerald-400">Vibe</span>
            <span className="text-neutral-100">2Prod</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              Dashboard
            </Link>
            <Link
              href="/scan/new"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              New Scan
            </Link>
            <Link
              href="/settings"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              Settings
            </Link>
            <Link
              href="/pricing"
              className="text-sm text-neutral-400 hover:text-neutral-100 transition-colors"
            >
              Pricing
            </Link>
            <UserButton
              appearance={{
                elements: {
                  avatarBox: "h-8 w-8",
                },
              }}
            />
          </div>
        </div>
      </nav>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  )
}
