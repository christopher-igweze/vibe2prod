"use client"

import { Suspense, useEffect, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { SignedIn, SignedOut, SignUp } from "@clerk/nextjs"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Loader2, CheckCircle, XCircle } from "lucide-react"
import { useUserRole } from "@/hooks/use-user-role"
import { apiFetch } from "@/lib/api/client"

function BetaActivation() {
  const { getToken } = useAuth()
  const { role, loading } = useUserRole()
  const router = useRouter()
  const searchParams = useSearchParams()
  const code = searchParams.get("code") ?? ""

  const [activating, setActivating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activated, setActivated] = useState(false)

  useEffect(() => {
    if (loading) return
    if (role === "beta_tester" || role === "developer") {
      router.replace("/dashboard")
      return
    }
    if (role === "user" && code && !activating && !activated && !error) {
      activate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, loading, code])

  async function activate() {
    setActivating(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const res = await apiFetch<{ status: string; role: string }>(
        "/api/beta/activate",
        { method: "POST", body: JSON.stringify({ code }), token },
      )
      if (res.status === "activated" || res.status === "already_active") {
        setActivated(true)
        setTimeout(() => router.replace("/onboarding"), 1500)
      }
    } catch {
      setError("Invalid or expired beta code. Check your invite link.")
    } finally {
      setActivating(false)
    }
  }

  if (loading || activating) {
    return (
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="size-6 animate-spin text-emerald-400" />
        <p className="text-neutral-400">
          {activating ? "Activating beta access..." : "Loading..."}
        </p>
      </div>
    )
  }

  if (activated) {
    return (
      <div className="flex flex-col items-center gap-3">
        <CheckCircle className="size-8 text-emerald-400" />
        <p className="text-emerald-400 font-medium">Beta access activated!</p>
        <p className="text-neutral-400 text-sm">Redirecting to onboarding...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3">
        <XCircle className="size-8 text-red-400" />
        <p className="text-red-400 font-medium">{error}</p>
        <p className="text-neutral-500 text-sm">
          Check the invite link you received and try again.
        </p>
      </div>
    )
  }

  if (role === "user" && !code) {
    return (
      <div className="text-center space-y-3">
        <p className="text-emerald-400 font-medium">
          You need a beta invite link to activate access.
        </p>
        <p className="text-neutral-400 text-sm">
          Contact{" "}
          <a
            href="https://linkedin.com/in/christopher-igweze"
            target="_blank"
            rel="noopener noreferrer"
            className="text-emerald-400 hover:text-emerald-300 underline"
          >
            Christopher on LinkedIn
          </a>{" "}
          to request an invite.
        </p>
        <Link
          href="/"
          className="inline-block mt-4 text-sm text-neutral-500 hover:text-neutral-300 underline"
        >
          Back to home
        </Link>
      </div>
    )
  }

  return null
}

function BetaSignup() {
  const searchParams = useSearchParams()
  const code = searchParams.get("code") ?? "FORGE2026"

  return (
    <SignUp
      forceRedirectUrl={`/beta?code=${code}`}
      appearance={{
        elements: {
          rootBox: "mx-auto",
          card: "bg-[#131825]/80 backdrop-blur-sm border border-white/[0.06]",
        },
      }}
    />
  )
}

export default function BetaPage() {
  return (
    <div className="min-h-screen bg-neutral-950 flex flex-col items-center justify-center px-6">
      <div className="text-center mb-12">
        <Link href="/" className="text-lg font-bold tracking-tight mb-8 inline-block">
          <span className="text-emerald-400">Vibe</span>
          <span className="text-neutral-100">2Prod</span>
        </Link>
        <div className="inline-flex items-center rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-1.5 text-sm text-emerald-400 mb-6">
          Private Beta
        </div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl mb-4 font-[family-name:var(--font-heading)]">
          Welcome to the{" "}
          <span className="text-emerald-400">FORGE</span> Beta
        </h1>
        <p className="text-lg text-neutral-400 max-w-xl mx-auto">
          You&apos;ve been invited to try Vibe2Prod before public launch. Sign
          up to activate your beta access and get 1 free scan credit.
        </p>
      </div>

      <Suspense fallback={<Loader2 className="size-6 animate-spin text-neutral-500" />}>
        <SignedOut>
          <BetaSignup />
        </SignedOut>

        <SignedIn>
          <BetaActivation />
        </SignedIn>
      </Suspense>
    </div>
  )
}
