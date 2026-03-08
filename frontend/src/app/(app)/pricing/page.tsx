"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { useSearchParams } from "next/navigation"
import { Loader2, Wallet, Plus } from "lucide-react"
import { apiFetch } from "@/lib/api/client"
import { useUserRole } from "@/hooks/use-user-role"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

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
        <Loader2 className="size-6 animate-spin text-neutral-500" />
      </div>
    )
  }

  const balance = profile?.balance_usd ?? 0

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Wallet</h1>
        {role === "developer" ? (
          <p className="text-emerald-400 font-medium">Unlimited Scans (Developer)</p>
        ) : (
          <div className="flex items-center justify-center gap-2">
            <Wallet className="size-5 text-emerald-400" />
            <span className="text-2xl font-bold text-emerald-400">
              ${balance.toFixed(2)}
            </span>
          </div>
        )}
      </div>

      {success && (
        <div className="mx-auto max-w-md rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-center">
          <p className="text-emerald-400 font-medium">Funds added successfully!</p>
          <p className="text-sm text-neutral-400 mt-1">Your wallet has been topped up.</p>
        </div>
      )}

      <div className="mx-auto max-w-lg space-y-6">
        <div className="text-center space-y-1">
          <p className="text-neutral-400">Pay only for what you use. Each scan costs the actual AI + infrastructure cost with a 4x markup.</p>
          <p className="text-sm text-emerald-400">$5 free balance included with signup</p>
        </div>

        {/* Cost estimate table */}
        <div className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 space-y-3">
          <p className="text-sm font-medium text-neutral-300">Estimated cost per scan</p>
          <div className="grid grid-cols-3 gap-3 text-center text-xs">
            <div className="rounded-lg bg-neutral-800/50 p-3">
              <div className="text-neutral-500 mb-1">Small repo</div>
              <div className="text-lg font-bold text-neutral-200">~$1</div>
              <div className="text-neutral-600">&lt;5k LOC</div>
            </div>
            <div className="rounded-lg bg-neutral-800/50 p-3">
              <div className="text-neutral-500 mb-1">Medium repo</div>
              <div className="text-lg font-bold text-neutral-200">~$3</div>
              <div className="text-neutral-600">5k-50k LOC</div>
            </div>
            <div className="rounded-lg bg-neutral-800/50 p-3">
              <div className="text-neutral-500 mb-1">Large repo</div>
              <div className="text-lg font-bold text-neutral-200">~$4</div>
              <div className="text-neutral-600">50k+ LOC</div>
            </div>
          </div>
        </div>

        {/* Quick deposit buttons */}
        <div className="space-y-3">
          <p className="text-sm font-medium text-neutral-300 text-center">Add funds</p>
          <div className="grid grid-cols-3 gap-3">
            {QUICK_AMOUNTS.map((opt) => (
              <Button
                key={opt.cents}
                variant="outline"
                className="h-12 text-lg border-neutral-700 hover:border-emerald-500/50 hover:bg-emerald-500/5"
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
              className="bg-neutral-900 border-neutral-700"
            />
            <Button
              className="bg-emerald-600 hover:bg-emerald-700 shrink-0"
              disabled={buying || !customAmount || parseFloat(customAmount) < 5}
              onClick={handleCustomDeposit}
            >
              <Plus className="size-4 mr-1" /> Add
            </Button>
          </div>
          <p className="text-xs text-neutral-600 text-center">Minimum deposit: $5.00</p>
        </div>
      </div>
    </div>
  )
}
