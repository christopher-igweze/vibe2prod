"use client"

import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import { useAuth, UserButton } from "@clerk/nextjs"
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
  const { isSignedIn, isLoaded } = useAuth()
  const { role, profile, loading } = useUserRole()

  const isProbeRoute = pathname.startsWith("/probe")

  useEffect(() => {
    if (loading || !isLoaded) return
    // Allow probe pages for anyone (including anonymous)
    if (isProbeRoute) return
    // Non-signed-in users shouldn't reach non-probe (app) routes
    if (!isSignedIn) return
    if (role === "user") {
      router.replace("/")
      return
    }
    if (profile && !profile.onboarding_complete && pathname !== "/onboarding") {
      router.replace("/onboarding")
    }
  }, [role, profile, loading, isLoaded, isSignedIn, pathname, router, isProbeRoute])

  if ((loading || !isLoaded) && !isProbeRoute) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="size-6 animate-spin text-forge-emerald" />
      </div>
    )
  }

  // Anonymous users on probe routes, or waitlisted/non-onboarded users: minimal nav
  if (!isSignedIn || role === "user" || (profile && !profile.onboarding_complete)) {
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
                href="/probe/new"
                className="text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
              >
                Live Probe
              </Link>
              {isSignedIn ? (
                <UserButton
                  appearance={{ elements: { avatarBox: "h-8 w-8" } }}
                />
              ) : (
                <Link
                  href="/sign-in"
                  className="rounded-lg bg-forge-emerald px-3 py-1.5 text-sm font-semibold text-[#0B0F19] hover:bg-forge-emerald-light transition-colors"
                >
                  Sign In
                </Link>
              )}
            </div>
          </div>
        </nav>
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
              href="/probe/new"
              className="text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
              data-tour="nav-probe"
            >
              Live Probe
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
