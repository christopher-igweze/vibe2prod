"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { UserButton } from "@clerk/nextjs"
import Link from "next/link"
import { Loader2, Wallet, HelpCircle } from "lucide-react"
import { useUserRole } from "@/hooks/use-user-role"
import { TourProvider, useTour } from "@/components/tour/tour-provider"

function HelpButton() {
  const { startCurrentPageTour } = useTour()
  return (
    <button
      onClick={startCurrentPageTour}
      className="text-[#4E586E] hover:text-forge-emerald transition-colors"
      title="Start guided tour"
    >
      <HelpCircle className="size-4" />
    </button>
  )
}

function AppLayoutInner({ children }: { children: React.ReactNode }) {
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
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="size-6 animate-spin text-forge-emerald" />
      </div>
    )
  }

  // Onboarding or waitlisted users: no nav, just the page content
  if (role === "user" || (profile && !profile.onboarding_complete)) {
    return (
      <div className="min-h-screen bg-background">
        <div className="mx-auto max-w-6xl px-6 py-3">
          <Link href="/" className="text-lg font-bold tracking-tight font-[family-name:var(--font-heading)]">
            <span className="forge-gradient-text">Vibe</span>
            <span className="text-foreground">2Prod</span>
          </Link>
        </div>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <nav className="forge-glass-nav sticky top-0 z-50">
        <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-3">
          <Link href="/" className="text-lg font-bold tracking-tight font-[family-name:var(--font-heading)]">
            <span className="forge-gradient-text">Vibe</span>
            <span className="text-foreground">2Prod</span>
          </Link>
          <div className="flex items-center gap-6">
            <Link
              href="/dashboard"
              className="text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
              data-tour="nav-dashboard"
            >
              Dashboard
            </Link>
            <Link
              href="/scan/new"
              className="text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
              data-tour="nav-new-scan"
            >
              New Scan
            </Link>
            <Link
              href="/settings"
              className="text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
              data-tour="settings-link"
            >
              Settings
            </Link>
            <Link
              href="/pricing"
              className="flex items-center gap-1.5 text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
              data-tour="wallet-link"
            >
              <Wallet className="size-4" />
              <span className="font-semibold text-forge-emerald">${(profile?.balance_usd ?? 0).toFixed(2)}</span>
            </Link>
            <HelpButton />
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

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <TourProvider>
      <AppLayoutInner>{children}</AppLayoutInner>
    </TourProvider>
  )
}
