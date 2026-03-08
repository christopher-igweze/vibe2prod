"use client"

import { Suspense, useEffect, useState } from "react"
import { useSearchParams, useRouter } from "next/navigation"
import { SignedIn, SignedOut, SignUp, SignIn } from "@clerk/nextjs"
import { useAuth } from "@clerk/nextjs"
import Link from "next/link"
import { Loader2, CheckCircle, XCircle, KeyRound } from "lucide-react"
import { useUserRole } from "@/hooks/use-user-role"
import { apiFetch } from "@/lib/api/client"
import { Button } from "@/components/ui/button"

const ACCEPTED_CODES = ["FORGE2026"]

function CodeGate({ onAccepted }: { onAccepted: (code: string) => void }) {
  const [input, setInput] = useState("")
  const [error, setError] = useState(false)

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const trimmed = input.trim().toUpperCase()
    if (ACCEPTED_CODES.includes(trimmed)) {
      setError(false)
      onAccepted(trimmed)
    } else {
      setError(true)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
      <div className="space-y-2">
        <label htmlFor="beta-code" className="text-sm text-[#8692A8]">
          Enter your beta invite code
        </label>
        <div className="flex gap-2">
          <input
            id="beta-code"
            type="text"
            value={input}
            onChange={(e) => { setInput(e.target.value); setError(false) }}
            placeholder="e.g. FORGE2026"
            className="flex-1 bg-forge-surface border border-white/[0.08] rounded-lg px-4 py-2.5 text-[#E8ECF4] placeholder:text-[#4E586E] focus:outline-none focus:border-forge-emerald/50 text-sm font-mono tracking-wider"
            autoFocus
          />
          <Button
            type="submit"
            className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19] px-6"
          >
            <KeyRound className="size-4 mr-1.5" />
            Verify
          </Button>
        </div>
        {error && (
          <p className="text-red-400 text-xs">Invalid code. Check your invite and try again.</p>
        )}
      </div>
    </form>
  )
}

function BetaActivation({ code }: { code: string }) {
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
    if (code && !activating && !activated && !error) {
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
  const searchParams = useSearchParams()
  const urlCode = searchParams.get("code") ?? ""
  const [acceptedCode, setAcceptedCode] = useState(urlCode)
  const codeVerified = ACCEPTED_CODES.includes(acceptedCode.toUpperCase())

  return (
    <>
      {!codeVerified ? (
        <CodeGate onAccepted={setAcceptedCode} />
      ) : (
        <>
          <SignedOut>
            <SignUp
              forceRedirectUrl={`/beta?code=${acceptedCode}`}
              appearance={{
                elements: {
                  rootBox: "mx-auto",
                  card: "bg-forge-surface/80 backdrop-blur-sm border border-white/[0.06]",
                },
              }}
            />
          </SignedOut>

          <SignedIn>
            <BetaActivation code={acceptedCode} />
          </SignedIn>
        </>
      )}
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
