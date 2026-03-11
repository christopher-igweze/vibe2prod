"use client"

export const dynamic = "force-dynamic"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { useRouter } from "next/navigation"
import {
  CheckCircle2,
  Loader2,
  Shield,
  ArrowLeft,
  ArrowRight,
  AlertCircle,
} from "lucide-react"

import { apiFetch, ApiError } from "@/lib/api/client"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"

// ---------------------------------------------------------------------------
// Step indicator (2 steps)
// ---------------------------------------------------------------------------

const STEPS = [
  { number: 1, label: "Target & Tests" },
  { number: 2, label: "Launch" },
] as const

function ProbeStepIndicator({ currentStep }: { currentStep: number }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {STEPS.map((step, i) => (
        <div key={step.number} className="flex items-center gap-2">
          <div
            className={`flex items-center justify-center size-8 rounded-full text-sm font-medium transition-colors ${
              currentStep === step.number
                ? "bg-forge-emerald text-[#0B0F19]"
                : currentStep > step.number
                  ? "bg-forge-emerald/20 text-forge-emerald"
                  : "bg-forge-surface text-[#4E586E] border border-white/[0.06]"
            }`}
          >
            {currentStep > step.number ? (
              <CheckCircle2 className="size-4" />
            ) : (
              step.number
            )}
          </div>
          <span
            className={`text-sm hidden sm:inline ${
              currentStep === step.number ? "text-foreground" : "text-[#4E586E]"
            }`}
          >
            {step.label}
          </span>
          {i < STEPS.length - 1 && (
            <div className="w-8 sm:w-12 h-px bg-white/[0.06] mx-1" />
          )}
        </div>
      ))}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Test category definitions
// ---------------------------------------------------------------------------

interface TestCategory {
  id: string
  label: string
  description: string
}

const TEST_CATEGORIES: TestCategory[] = [
  { id: "security_headers", label: "Security Headers", description: "Check for missing or misconfigured security headers (CSP, HSTS, X-Frame-Options)" },
  { id: "sensitive_data", label: "Sensitive Data Exposure", description: "Detect exposed API keys, tokens, or PII in responses" },
  { id: "cookie_security", label: "Cookie Security", description: "Verify Secure, HttpOnly, and SameSite cookie attributes" },
  { id: "ssl_tls", label: "SSL/TLS", description: "Validate certificate chain, protocol versions, and cipher suites" },
  { id: "sql_injection", label: "SQL Injection", description: "Test for SQL injection vectors in query parameters and form inputs" },
  { id: "xss", label: "XSS (Cross-Site Scripting)", description: "Probe for reflected and stored XSS vulnerabilities" },
  { id: "csrf", label: "CSRF Protection", description: "Verify anti-CSRF tokens and SameSite cookie enforcement" },
  { id: "server_misconfig", label: "Server Misconfiguration", description: "Check for directory listing, debug endpoints, default credentials" },
  { id: "open_redirects", label: "Open Redirects", description: "Test for unvalidated redirect parameters" },
  { id: "auth_issues", label: "Authentication Issues", description: "Check for broken auth, session fixation, and brute-force vulnerabilities" },
]

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function NewProbePage() {
  const { getToken, isSignedIn } = useAuth()
  const router = useRouter()

  // Wizard step
  const [step, setStep] = useState(1)

  // Step 1: URL + Test Configuration
  const [targetUrl, setTargetUrl] = useState("")

  const [selectedTests, setSelectedTests] = useState<Set<string>>(
    new Set(TEST_CATEGORIES.map((c) => c.id))
  )

  // Quota
  const [quota, setQuota] = useState<{ onboarded: boolean; remaining: number; limit: number } | null>(null)

  useEffect(() => {
    let cancelled = false
    async function loadQuota() {
      try {
        const token = isSignedIn ? ((await getToken()) ?? undefined) : undefined
        const data = await apiFetch<{ onboarded: boolean; remaining: number; limit: number }>("/api/probe/quota", { token })
        if (!cancelled) setQuota(data)
      } catch { /* non-critical */ }
    }
    loadQuota()
    return () => { cancelled = true }
  }, [getToken, isSignedIn])

  // Step 2: Submit
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  const isValidUrl = (url: string) => {
    try {
      const parsed = new URL(url.trim())
      return parsed.protocol === "https:" || parsed.protocol === "http:"
    } catch {
      return false
    }
  }

  const toggleTest = (id: string) => {
    setSelectedTests((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedTests.size === TEST_CATEGORIES.length) {
      setSelectedTests(new Set())
    } else {
      setSelectedTests(new Set(TEST_CATEGORIES.map((c) => c.id)))
    }
  }

  const handleSubmit = async () => {
    setSubmitting(true)
    setSubmitError(null)

    try {
      const token = isSignedIn ? ((await getToken()) ?? undefined) : undefined
      const resp = await apiFetch<{ probe_id: string }>("/api/probe", {
        method: "POST",
        body: JSON.stringify({
          target_url: targetUrl.trim(),
          probe_type: "security",
          config: {
            tests: Array.from(selectedTests),
          },
        }),
        token,
      })

      router.push(`/probe/${resp.probe_id}`)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setSubmitError("Rate limited. Please wait a moment and try again.")
        } else {
          setSubmitError(err.message || "Failed to start probe")
        }
      } else {
        setSubmitError("An unexpected error occurred")
      }
    } finally {
      setSubmitting(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  const domain = (() => {
    try { return new URL(targetUrl.trim()).hostname } catch { return "" }
  })()

  return (
    <div className="max-w-2xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-100 mb-1 font-[family-name:var(--font-heading)]">
          Live Probe
        </h1>
        <p className="text-[#8692A8] text-sm">
          Test your deployed application for security vulnerabilities in real-time.
        </p>
        {quota && !quota.onboarded && (
          <div className="mt-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-forge-emerald/5 border border-forge-emerald/20 text-xs">
            <Shield className="size-3.5 text-forge-emerald shrink-0" />
            <span className="text-[#8692A8]">
              <span className="text-forge-emerald font-semibold">{quota.remaining}</span> of {quota.limit} free probes remaining.
              {quota.remaining === 0
                ? isSignedIn
                  ? <> <a href="/onboarding" className="text-forge-emerald hover:underline font-medium">Complete onboarding</a> for unlimited probes.</>
                  : <> <a href="/sign-up" className="text-forge-emerald hover:underline font-medium">Sign up</a> for unlimited probes.</>
                : isSignedIn
                  ? <> <a href="/onboarding" className="text-forge-emerald hover:underline font-medium">Onboard</a> for unlimited probes + detailed reports.</>
                  : <> <a href="/sign-up" className="text-forge-emerald hover:underline font-medium">Sign up</a> for unlimited probes + detailed reports.</>
              }
            </span>
          </div>
        )}
      </div>

      <ProbeStepIndicator currentStep={step} />

      {/* ── Step 1: Target URL + Test Configuration ── */}
      {step === 1 && (
        <Card className="forge-glass-card p-6 space-y-6">
          <div className="space-y-2">
            <Label htmlFor="target-url" className="text-sm font-medium text-[#E8ECF4]">
              Target URL
            </Label>
            <Input
              id="target-url"
              placeholder="https://myapp.com"
              value={targetUrl}
              onChange={(e) => setTargetUrl(e.target.value)}
              className="bg-[#131825] border-white/[0.06] text-[#E8ECF4] placeholder:text-[#4E586E]"
            />
            {targetUrl.trim() && !isValidUrl(targetUrl) && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="size-3" /> Enter a valid URL (e.g., https://myapp.com)
              </p>
            )}
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold text-[#E8ECF4]">Security Tests</h2>
                <p className="text-xs text-[#8692A8] mt-0.5">
                  Select which tests to run{domain ? ` against ${domain}` : ""}
                </p>
              </div>
              <button
                onClick={toggleAll}
                className="text-xs text-forge-emerald hover:text-forge-emerald/80 transition-colors font-medium"
              >
                {selectedTests.size === TEST_CATEGORIES.length ? "Deselect All" : "Select All"}
              </button>
            </div>

            <div className="space-y-2">
              {TEST_CATEGORIES.map((cat) => (
                <label
                  key={cat.id}
                  className={`flex items-start gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                    selectedTests.has(cat.id)
                      ? "bg-forge-emerald/5 border border-forge-emerald/20"
                      : "bg-[#131825]/50 border border-white/[0.04] hover:border-white/[0.08]"
                  }`}
                >
                  <Checkbox
                    checked={selectedTests.has(cat.id)}
                    onCheckedChange={() => toggleTest(cat.id)}
                    className="mt-0.5 border-white/[0.15] data-[state=checked]:bg-forge-emerald data-[state=checked]:border-forge-emerald"
                  />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-[#E8ECF4]">{cat.label}</p>
                    <p className="text-xs text-[#8692A8] mt-0.5">{cat.description}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <Button
              onClick={() => setStep(2)}
              disabled={!isValidUrl(targetUrl) || selectedTests.size === 0}
              className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
            >
              Review
              <ArrowRight className="size-4 ml-1.5" />
            </Button>
          </div>
        </Card>
      )}

      {/* ── Step 2: Review + Launch ── */}
      {step === 2 && (
        <Card className="forge-glass-card p-6 space-y-6">
          <h2 className="text-lg font-semibold text-[#E8ECF4]">Review &amp; Launch</h2>

          <div className="space-y-4">
            <div className="rounded-lg bg-[#131825] border border-white/[0.06] p-4 space-y-3">
              <p className="text-xs text-[#8692A8] uppercase tracking-wider">Target</p>
              <p className="text-sm text-[#E8ECF4] font-medium break-all">{targetUrl}</p>
            </div>

            <div className="rounded-lg bg-[#131825] border border-white/[0.06] p-4 space-y-2">
              <p className="text-xs text-[#8692A8] uppercase tracking-wider">Tests</p>
              <p className="text-sm text-[#E8ECF4]">
                {selectedTests.size} of {TEST_CATEGORIES.length} security tests selected
              </p>
              <div className="flex flex-wrap gap-1.5 mt-1">
                {TEST_CATEGORIES.filter((c) => selectedTests.has(c.id)).map((c) => (
                  <Badge
                    key={c.id}
                    variant="outline"
                    className="border-white/[0.08] text-[#8692A8] text-xs"
                  >
                    {c.label}
                  </Badge>
                ))}
              </div>
            </div>
          </div>

          {submitError && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/30">
              <AlertCircle className="size-4 text-red-400 shrink-0" />
              <p className="text-sm text-red-400">{submitError}</p>
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <Button
              variant="ghost"
              onClick={() => setStep(1)}
              className="text-[#8692A8] hover:text-[#E8ECF4]"
            >
              <ArrowLeft className="size-4 mr-1.5" />
              Back
            </Button>
            <Button
              onClick={handleSubmit}
              disabled={submitting}
              className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
            >
              {submitting ? (
                <>
                  <Loader2 className="size-4 animate-spin mr-1.5" />
                  Starting Probe...
                </>
              ) : (
                <>
                  <Shield className="size-4 mr-1.5" />
                  Start Probe
                </>
              )}
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
