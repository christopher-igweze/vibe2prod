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
    <div className="relative group">
      <button
        onClick={startCurrentPageTour}
        aria-label="Start guided tour"
        className="text-[#4E586E] hover:text-forge-emerald transition-colors flex items-center"
      >
        <HelpCircle className="size-4" />
      </button>
      <span
        role="tooltip"
        className="pointer-events-none absolute right-0 top-full mt-2 whitespace-nowrap rounded-md border border-white/10 bg-[#0f1420] px-2.5 py-1 text-xs text-[#E8ECF4] opacity-0 shadow-lg transition-opacity group-hover:opacity-100"
      >
        Start guided tour
      </span>
    </div>
  )
}

function AppLayoutInner({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isSignedIn, isLoaded } = useAuth()
  const { role, profile, loading } = useUserRole()

  useEffect(() => {
    if (loading || !isLoaded) return
    if (!isSignedIn) return
    if (profile && !profile.onboarding_complete && pathname !== "/onboarding") {
      router.replace("/onboarding")
    }
  }, [profile, loading, isLoaded, isSignedIn, pathname, router])

  if (loading || !isLoaded) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Loader2 className="size-6 animate-spin text-forge-emerald" />
      </div>
    )
  }

  // Non-signed-in or non-onboarded users: minimal nav
  if (!isSignedIn || (profile && !profile.onboarding_complete)) {
    return (
      <div className="min-h-screen bg-background">
        <nav className="forge-glass-nav sticky top-0 z-50">
          <div className="mx-auto max-w-6xl flex items-center justify-between px-6 py-3">
            <Link href="/" className="text-lg font-bold tracking-tight font-[family-name:var(--font-heading)]">
              <span className="forge-gradient-text">Vibe</span>
              <span className="text-foreground">2Prod</span>
            </Link>
            <div className="flex items-center gap-6">
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
              href="/settings"
              className="text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
              data-tour="settings-link"
            >
              Settings
            </Link>
            {role !== "developer" && (
              <Link
                href="/pricing"
                className="flex items-center gap-1.5 text-sm text-[#8692A8] hover:text-forge-emerald transition-colors"
                data-tour="wallet-link"
              >
                <Wallet className="size-4" />
                {profile?.has_openrouter_key ? (
                  <span className="text-[11px] bg-forge-emerald/20 text-forge-emerald px-2 py-0.5 rounded-full font-semibold">
                    BYOK
                  </span>
                ) : (
                  <span className="font-semibold text-forge-emerald">${(profile?.balance_usd ?? 0).toFixed(2)}</span>
                )}
              </Link>
            )}
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
