"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { Loader2, Plus, Coffee } from "lucide-react"
import { apiFetch } from "@/lib/api/client"
import { useUserRole } from "@/hooks/use-user-role"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { IconWallet } from "@/components/landing/landing-icons"

const QUICK_AMOUNTS = [
  { cents: 500, label: "$5" },
  { cents: 2000, label: "$20" },
  { cents: 5000, label: "$50" },
]

export default function PricingPage() {
  const { getToken } = useAuth()
  const { role, profile, loading: roleLoading } = useUserRole()
  const searchParams = useSearchParams()
  const [buying, setBuying] = useState(false)
  const [success, setSuccess] = useState(false)
  const [customAmount, setCustomAmount] = useState("")

  useEffect(() => {
    if (searchParams.get("success") === "true") {
      setSuccess(true)
    }
  }, [searchParams])

  async function handleDeposit(amountCents: number) {
    setBuying(true)
    try {
      const token = (await getToken()) ?? undefined
      const res = await apiFetch<{ checkout_url: string }>("/api/credits/checkout", {
        method: "POST",
        body: JSON.stringify({ amount_cents: amountCents }),
        token,
      })
      window.location.href = res.checkout_url
    } catch {
      setBuying(false)
    }
  }

  function handleCustomDeposit() {
    const dollars = parseFloat(customAmount)
    if (isNaN(dollars) || dollars < 5) return
    handleDeposit(Math.round(dollars * 100))
  }

  if (roleLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-6 animate-spin text-[#4E586E]" />
      </div>
    )
  }

  const balance = profile?.balance_usd ?? 0

  return (
    <div className="space-y-8 max-w-2xl mx-auto">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)]">Wallet</h1>
        {role === "developer" ? (
          <p className="text-forge-emerald font-medium">Unlimited Scans (Developer)</p>
        ) : (
          <div className="flex items-center justify-center gap-2">
            <IconWallet className="size-5 text-forge-emerald" />
            <span className="text-2xl font-bold text-forge-emerald">
              ${balance.toFixed(2)}
            </span>
          </div>
        )}
      </div>

      {success && (
        <div className="mx-auto max-w-md rounded-lg border border-forge-emerald/30 bg-forge-emerald/10 p-4 text-center">
          <p className="text-forge-emerald font-medium">Funds added successfully!</p>
          <p className="text-sm text-[#8692A8] mt-1">Your wallet has been topped up. Thanks for the coffee ☕</p>
        </div>
      )}

      {/* Honest pricing pitch */}
      <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-5 space-y-3">
        <div className="flex items-start gap-3">
          <div className="shrink-0 size-10 rounded-lg bg-amber-400/10 border border-amber-400/20 flex items-center justify-center">
            <Coffee className="size-5 text-amber-300" />
          </div>
          <div className="space-y-2">
            <p className="font-semibold text-[#E8ECF4]">
              Real talk: paying here is basically buying the maintainer a coffee.
            </p>
            <p className="text-sm text-[#8692A8] leading-relaxed">
              The web UI runs the exact same FORGE engine but with a small markup on the OpenRouter bill to cover sandboxing and a croissant. If you just want the cheapest scans,{" "}
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="text-forge-emerald underline hover:text-forge-emerald-light"
              >
                grab an OpenRouter API key
              </a>
              , drop it in{" "}
              <Link href="/settings" className="text-forge-emerald underline hover:text-forge-emerald-light">
                Settings
              </Link>
              , and switch to BYOK. LLM calls bill directly to you at cost — no middleman, no markup.
            </p>
            <p className="text-sm text-[#8692A8] leading-relaxed">
              <span className="text-forge-emerald font-semibold">Zero-dollar mode:</span>{" "}
              don&rsquo;t even have an OpenRouter key? FORGE still runs the 16 Opengrep rules, deterministic scoring, and the Production Readiness Score with no API key at all. You miss the two LLM passes (Codebase Analyst + Security Auditor) but the static scan is free forever — grab the CLI at{" "}
              <Link href="/#setup" className="text-forge-emerald underline hover:text-forge-emerald-light">
                Set up in 60 seconds
              </Link>
              .
            </p>
          </div>
        </div>
      </div>

      <div className="space-y-6">
        <div className="text-center space-y-1">
          <p className="text-[#8692A8]">Still want to pay for convenience? No judgment.</p>
          <p className="text-sm text-forge-emerald">$15 free balance included with signup — that&rsquo;s a handful of free scans before you pick a side.</p>
        </div>

        {/* Cost estimate table */}
        <div className="rounded-xl border border-white/[0.06] bg-forge-surface/50 p-4 space-y-3">
          <p className="text-sm font-medium text-[#E8ECF4]">Managed web UI — estimated cost per scan</p>
          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div className="rounded-lg bg-forge-nav/50 p-3">
              <div className="text-[#4E586E] mb-1">Small repo</div>
              <div className="text-lg font-bold text-[#E8ECF4]">~$2</div>
              <div className="text-[#4E586E]">&lt;5k LOC</div>
            </div>
            <div className="rounded-lg bg-forge-nav/50 p-3">
              <div className="text-[#4E586E] mb-1">Medium repo</div>
              <div className="text-lg font-bold text-[#E8ECF4]">~$6</div>
              <div className="text-[#4E586E]">5k-50k LOC</div>
            </div>
            <div className="rounded-lg bg-forge-nav/50 p-3">
              <div className="text-[#4E586E] mb-1">Large repo</div>
              <div className="text-lg font-bold text-[#E8ECF4]">~$8</div>
              <div className="text-[#4E586E]">50k+ LOC</div>
            </div>
          </div>
        </div>

        {/* BYOK pricing */}
        <div className="rounded-xl border border-forge-emerald/20 bg-forge-emerald/5 p-4 space-y-3">
          <p className="text-sm font-medium text-[#E8ECF4]">BYOK pricing <span className="text-xs text-forge-emerald font-normal">(Bring Your Own Key — billed directly to OpenRouter, no markup)</span></p>
          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div className="rounded-lg bg-forge-nav/50 p-3">
              <div className="text-[#4E586E] mb-1">Small repo</div>
              <div className="text-lg font-bold text-forge-emerald">~$0.40</div>
              <div className="text-[#4E586E]">&lt;5k LOC</div>
            </div>
            <div className="rounded-lg bg-forge-nav/50 p-3">
              <div className="text-[#4E586E] mb-1">Medium repo</div>
              <div className="text-lg font-bold text-forge-emerald">~$1.50</div>
              <div className="text-[#4E586E]">5k-50k LOC</div>
            </div>
            <div className="rounded-lg bg-forge-nav/50 p-3">
              <div className="text-[#4E586E] mb-1">Large repo</div>
              <div className="text-lg font-bold text-forge-emerald">~$2.00</div>
              <div className="text-[#4E586E]">50k+ LOC</div>
            </div>
          </div>
          <p className="text-xs text-[#8692A8] text-center">
            Save your OpenRouter key in{" "}
            <Link href="/settings" className="text-forge-emerald hover:underline">Settings</Link>
            {" "}to enable BYOK.
          </p>
        </div>

        {/* Quick deposit buttons */}
        <div className="space-y-3">
          <p className="text-sm font-medium text-[#E8ECF4] text-center">Add funds (or, you know, buy the coffee)</p>
          <div className="grid grid-cols-3 gap-3">
            {QUICK_AMOUNTS.map((opt) => (
              <Button
                key={opt.cents}
                variant="outline"
                className="h-12 text-lg border-white/[0.06] hover:border-forge-emerald/50 hover:bg-forge-emerald/5"
                disabled={buying}
                onClick={() => handleDeposit(opt.cents)}
              >
                {buying ? <Loader2 className="size-4 animate-spin" /> : opt.label}
              </Button>
            ))}
          </div>

          {/* Custom amount */}
          <div className="flex gap-2">
            <Input
              type="number"
              min="5"
              step="1"
              placeholder="Custom amount ($5 min)"
              value={customAmount}
              onChange={(e) => setCustomAmount(e.target.value)}
              className="bg-forge-surface border-white/[0.06]"
            />
            <Button
              className="bg-forge-emerald hover:bg-forge-emerald/90 text-[#0B0F19] shrink-0"
              disabled={buying || !customAmount || parseFloat(customAmount) < 5}
              onClick={handleCustomDeposit}
            >
              <Plus className="size-4 mr-1" /> Add
            </Button>
          </div>
          <p className="text-xs text-[#4E586E] text-center">Minimum deposit: $5.00</p>
        </div>
      </div>
    </div>
  )
}
