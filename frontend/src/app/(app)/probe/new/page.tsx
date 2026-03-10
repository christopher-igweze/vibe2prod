"use client"

export const dynamic = "force-dynamic"

import { useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { useRouter } from "next/navigation"
import {
  CheckCircle2,
  Loader2,
  Shield,
  Globe,
  ArrowLeft,
  ArrowRight,
  AlertCircle,
} from "lucide-react"

import { apiFetch, ApiError } from "@/lib/api/client"
import type { AuthorizeResponse, VerifyResponse } from "@/lib/api/types"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Checkbox } from "@/components/ui/checkbox"

// ---------------------------------------------------------------------------
// Step indicator (probe-specific: 3 steps)
// ---------------------------------------------------------------------------

const STEPS = [
  { number: 1, label: "Authorization" },
  { number: 2, label: "Configuration" },
  { number: 3, label: "Launch" },
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
// Verification methods
// ---------------------------------------------------------------------------

type VerificationMethod = "dns_txt" | "meta_tag" | "file_upload"

const VERIFICATION_METHODS: { value: VerificationMethod; label: string }[] = [
  { value: "dns_txt", label: "DNS TXT Record" },
  { value: "meta_tag", label: "HTML Meta Tag" },
  { value: "file_upload", label: "File Upload" },
]

// ---------------------------------------------------------------------------
// Main Page
// ---------------------------------------------------------------------------

export default function NewProbePage() {
  const { getToken } = useAuth()
  const router = useRouter()

  // Wizard step
  const [step, setStep] = useState(1)

  // Step 1: URL + Authorization
  const [targetUrl, setTargetUrl] = useState("")
  const [authorizing, setAuthorizing] = useState(false)
  const [authResponse, setAuthResponse] = useState<AuthorizeResponse | null>(null)
  const [verified, setVerified] = useState(false)
  const [verifying, setVerifying] = useState(false)
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const [authError, setAuthError] = useState<string | null>(null)
  const [verificationMethod, setVerificationMethod] = useState<VerificationMethod>("dns_txt")

  // Step 2: Test Configuration
  const [selectedTests, setSelectedTests] = useState<Set<string>>(
    new Set(TEST_CATEGORIES.map((c) => c.id))
  )

  // Step 3: Submit
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // ---------------------------------------------------------------------------
  // Step 1 handlers
  // ---------------------------------------------------------------------------

  const isValidUrl = (url: string) => {
    try {
      const parsed = new URL(url.trim())
      return parsed.protocol === "https:" || parsed.protocol === "http:"
    } catch {
      return false
    }
  }

  const handleAuthorize = async () => {
    if (!isValidUrl(targetUrl)) {
      setAuthError("Please enter a valid URL (e.g., https://myapp.com)")
      return
    }
    setAuthorizing(true)
    setAuthError(null)
    setAuthResponse(null)
    setVerified(false)

    try {
      const token = (await getToken()) ?? undefined
      const resp = await apiFetch<AuthorizeResponse>("/api/probe/authorize", {
        method: "POST",
        body: JSON.stringify({ target_url: targetUrl.trim() }),
        token,
      })

      if (resp.method === "already_verified") {
        setVerified(true)
      } else {
        setAuthResponse(resp)
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setAuthError(err.message || "Authorization check failed")
      } else {
        setAuthError("An unexpected error occurred")
      }
    } finally {
      setAuthorizing(false)
    }
  }

  const handleVerify = async () => {
    setVerifying(true)
    setVerifyError(null)

    try {
      const token = (await getToken()) ?? undefined
      const resp = await apiFetch<VerifyResponse>("/api/probe/verify", {
        method: "POST",
        body: JSON.stringify({
          target_url: targetUrl.trim(),
          method: verificationMethod,
        }),
        token,
      })

      if (resp.verified) {
        setVerified(true)
      } else {
        setVerifyError(resp.message || "Verification failed. Please check your setup and try again.")
      }
    } catch (err) {
      if (err instanceof ApiError) {
        setVerifyError(err.message || "Verification failed")
      } else {
        setVerifyError("An unexpected error occurred")
      }
    } finally {
      setVerifying(false)
    }
  }

  // ---------------------------------------------------------------------------
  // Step 2 handlers
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Step 3: Submit
  // ---------------------------------------------------------------------------

  const handleSubmit = async () => {
    setSubmitting(true)
    setSubmitError(null)

    try {
      const token = (await getToken()) ?? undefined
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
      </div>

      <ProbeStepIndicator currentStep={step} />

      {/* ── Step 1: URL + Authorization ── */}
      {step === 1 && (
        <Card className="forge-glass-card p-6 space-y-6">
          <div className="space-y-2">
            <Label htmlFor="target-url" className="text-sm font-medium text-[#E8ECF4]">
              Target URL
            </Label>
            <div className="flex gap-2">
              <Input
                id="target-url"
                placeholder="https://myapp.com"
                value={targetUrl}
                onChange={(e) => {
                  setTargetUrl(e.target.value)
                  setVerified(false)
                  setAuthResponse(null)
                  setAuthError(null)
                }}
                className="bg-[#131825] border-white/[0.06] text-[#E8ECF4] placeholder:text-[#4E586E]"
              />
              <Button
                onClick={handleAuthorize}
                disabled={!targetUrl.trim() || authorizing}
                className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19] shrink-0"
              >
                {authorizing ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  <>
                    <Globe className="size-4 mr-1.5" />
                    Check
                  </>
                )}
              </Button>
            </div>
            {authError && (
              <p className="text-xs text-red-400 flex items-center gap-1">
                <AlertCircle className="size-3" /> {authError}
              </p>
            )}
          </div>

          {/* Domain verified */}
          {verified && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-forge-emerald/10 border border-forge-emerald/30">
              <CheckCircle2 className="size-4 text-forge-emerald" />
              <span className="text-sm text-forge-emerald font-medium">
                Domain verified: {domain}
              </span>
            </div>
          )}

          {/* Verification instructions */}
          {authResponse && !verified && (
            <div className="space-y-4">
              <div className="rounded-lg bg-[#131825] border border-white/[0.06] p-4 space-y-3">
                <div className="flex items-center gap-2">
                  <Shield className="size-4 text-forge-emerald" />
                  <p className="text-sm font-medium text-[#E8ECF4]">
                    Domain verification required
                  </p>
                </div>
                <p className="text-xs text-[#8692A8]">
                  Verify you own <span className="text-[#E8ECF4] font-medium">{domain}</span> using one of the methods below:
                </p>

                {/* Method selection */}
                <div className="flex flex-wrap gap-2">
                  {VERIFICATION_METHODS.map((m) => (
                    <button
                      key={m.value}
                      onClick={() => setVerificationMethod(m.value)}
                      className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                        verificationMethod === m.value
                          ? "bg-forge-emerald/20 text-forge-emerald border border-forge-emerald/30"
                          : "bg-[#0B0F19] text-[#8692A8] border border-white/[0.06] hover:border-white/[0.12]"
                      }`}
                    >
                      {m.label}
                    </button>
                  ))}
                </div>

                {/* Method instructions */}
                <div className="rounded-md bg-[#0B0F19] border border-white/[0.04] p-3">
                  {verificationMethod === "dns_txt" && (
                    <div className="space-y-1">
                      <p className="text-xs text-[#8692A8]">Add a DNS TXT record to your domain:</p>
                      <code className="block text-xs text-forge-emerald bg-[#131825] px-2 py-1.5 rounded font-mono break-all">
                        vibe2prod-verify={authResponse.token}
                      </code>
                    </div>
                  )}
                  {verificationMethod === "meta_tag" && (
                    <div className="space-y-1">
                      <p className="text-xs text-[#8692A8]">Add this meta tag to your homepage:</p>
                      <code className="block text-xs text-forge-emerald bg-[#131825] px-2 py-1.5 rounded font-mono break-all">
                        {`<meta name="vibe2prod-verify" content="${authResponse.token}" />`}
                      </code>
                    </div>
                  )}
                  {verificationMethod === "file_upload" && (
                    <div className="space-y-1">
                      <p className="text-xs text-[#8692A8]">Create this file at your domain root:</p>
                      <code className="block text-xs text-forge-emerald bg-[#131825] px-2 py-1.5 rounded font-mono break-all">
                        /.well-known/vibe2prod-verify.txt
                      </code>
                      <p className="text-xs text-[#8692A8] mt-1">With content:</p>
                      <code className="block text-xs text-forge-emerald bg-[#131825] px-2 py-1.5 rounded font-mono break-all">
                        {authResponse.token}
                      </code>
                    </div>
                  )}
                </div>

                {verifyError && (
                  <p className="text-xs text-red-400 flex items-center gap-1">
                    <AlertCircle className="size-3" /> {verifyError}
                  </p>
                )}

                <Button
                  onClick={handleVerify}
                  disabled={verifying}
                  className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
                >
                  {verifying ? (
                    <Loader2 className="size-4 animate-spin mr-1.5" />
                  ) : (
                    <Shield className="size-4 mr-1.5" />
                  )}
                  Verify Domain
                </Button>
              </div>
            </div>
          )}

          {/* Continue button */}
          {verified && (
            <div className="flex justify-end">
              <Button
                onClick={() => setStep(2)}
                className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
              >
                Continue
                <ArrowRight className="size-4 ml-1.5" />
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* ── Step 2: Test Configuration ── */}
      {step === 2 && (
        <Card className="forge-glass-card p-6 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-[#E8ECF4]">Test Configuration</h2>
              <p className="text-xs text-[#8692A8] mt-1">
                Select which security tests to run against {domain}
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
              onClick={() => setStep(3)}
              disabled={selectedTests.size === 0}
              className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19]"
            >
              Review
              <ArrowRight className="size-4 ml-1.5" />
            </Button>
          </div>
        </Card>
      )}

      {/* ── Step 3: Review + Launch ── */}
      {step === 3 && (
        <Card className="forge-glass-card p-6 space-y-6">
          <h2 className="text-lg font-semibold text-[#E8ECF4]">Review &amp; Launch</h2>

          <div className="space-y-4">
            <div className="rounded-lg bg-[#131825] border border-white/[0.06] p-4 space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-[#8692A8] uppercase tracking-wider">Target</p>
                <Badge variant="outline" className="border-forge-emerald/30 text-forge-emerald text-xs">
                  Verified
                </Badge>
              </div>
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
              onClick={() => setStep(2)}
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
