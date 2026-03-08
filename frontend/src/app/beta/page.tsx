"use client"

import { Suspense, useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { SignedIn, SignedOut, SignUp } from "@clerk/nextjs"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Loader2, CheckCircle, XCircle } from "lucide-react"
import { useUserRole } from "@/hooks/use-user-role"
import { apiFetch } from "@/lib/api/client"
import { Button } from "@/components/ui/button"

function BetaActivation() {
  const { getToken } = useAuth()
  const { role, loading } = useUserRole()
  const router = useRouter()

  const [activating, setActivating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activated, setActivated] = useState(false)

  useEffect(() => {
    if (loading) return
    if (role === "beta_tester" || role === "developer") {
      router.replace("/dashboard")
      return
    }
    if (!activating && !activated && !error) {
      activate()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [role, loading])

  async function activate() {
    setActivating(true)
    setError(null)
    try {
      const token = (await getToken()) ?? undefined
      const res = await apiFetch<{ status: string; role: string }>(
        "/api/beta/activate",
        { method: "POST", token },
      )
      if (res.status === "activated" || res.status === "already_active") {
        setActivated(true)
        setTimeout(() => router.replace("/onboarding"), 1500)
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Activation failed"
      setError(msg)
    } finally {
      setActivating(false)
    }
  }

  if (loading || activating) {
    return (
      <div className="flex flex-col items-center gap-3">
        <Loader2 className="size-6 animate-spin text-forge-emerald" />
        <p className="text-[#8692A8]">
          {activating ? "Activating beta access..." : "Loading..."}
        </p>
      </div>
    )
  }

  if (activated) {
    return (
      <div className="flex flex-col items-center gap-3">
        <CheckCircle className="size-8 text-forge-emerald" />
        <p className="text-forge-emerald font-medium">Beta access activated!</p>
        <p className="text-[#8692A8] text-sm">Redirecting to onboarding...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center gap-3">
        <XCircle className="size-8 text-red-400" />
        <p className="text-red-400 font-medium">Activation failed</p>
        <p className="text-[#4E586E] text-sm">{error}</p>
        <Button
          variant="outline"
          size="sm"
          className="border-white/[0.08] mt-2"
          onClick={() => { setError(null); activate() }}
        >
          Retry
        </Button>
      </div>
    )
  }

  return null
}

function BetaContent() {
  return (
    <>
      <SignedOut>
        <SignUp
          forceRedirectUrl="/beta"
          appearance={{
            elements: {
              rootBox: "mx-auto",
              card: "bg-forge-surface/80 backdrop-blur-sm border border-white/[0.06]",
            },
          }}
        />
      </SignedOut>

      <SignedIn>
        <BetaActivation />
      </SignedIn>
    </>
  )
}

export default function BetaPage() {
  return (
    <div className="min-h-screen bg-forge-bg flex flex-col items-center justify-center px-6">
      <div className="text-center mb-10">
        <Link href="/" className="text-lg font-bold tracking-tight mb-8 inline-block">
          <span className="text-forge-emerald">Vibe</span>
          <span className="text-[#E8ECF4]">2Prod</span>
        </Link>
        <div className="inline-flex items-center rounded-full border border-forge-emerald/20 bg-forge-emerald/10 px-4 py-1.5 text-sm text-forge-emerald mb-6">
          Private Beta
        </div>
        <h1 className="text-4xl font-bold tracking-tight sm:text-5xl mb-4 font-[family-name:var(--font-heading)] text-[#E8ECF4]">
          Welcome to the{" "}
          <span className="text-forge-emerald">Beta</span>
        </h1>
        <p className="text-lg text-[#8692A8] max-w-xl mx-auto">
          Sign up to get <span className="text-forge-emerald font-semibold">$15.00 free balance</span> and start scanning your repos.
        </p>
      </div>

      <Suspense fallback={<Loader2 className="size-6 animate-spin text-[#4E586E]" />}>
        <BetaContent />
      </Suspense>

      <Link
        href="/"
        className="mt-8 text-sm text-[#4E586E] hover:text-[#8692A8] underline"
      >
        Back to home
      </Link>
    </div>
  )
}
