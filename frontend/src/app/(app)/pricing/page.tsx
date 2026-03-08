"use client"

import { useEffect, useState } from "react"
import { useAuth } from "@clerk/nextjs"
import { useSearchParams } from "next/navigation"
import { Loader2 } from "lucide-react"
import { apiFetch } from "@/lib/api/client"
import { useUserRole } from "@/hooks/use-user-role"
import { Button } from "@/components/ui/button"

const PACKAGES = [
  { id: "single", name: "Single", credits: 1, price: "$10", perScan: "$10/scan", highlight: false },
  { id: "pack", name: "Pack", credits: 5, price: "$40", perScan: "$8/scan", highlight: true },
  { id: "bulk", name: "Bulk", credits: 15, price: "$99", perScan: "$6.60/scan", highlight: false },
]

export default function PricingPage() {
  const { getToken } = useAuth()
  const { role, profile, loading: roleLoading } = useUserRole()
  const searchParams = useSearchParams()
  const [buyingId, setBuyingId] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (searchParams.get("success") === "true") {
      setSuccess(true)
    }
  }, [searchParams])

  async function handleBuy(packageId: string) {
    setBuyingId(packageId)
    try {
      const token = (await getToken()) ?? undefined
      const res = await apiFetch<{ checkout_url: string }>("/api/credits/checkout", {
        method: "POST",
        body: JSON.stringify({ package_id: packageId }),
        token,
      })
      window.location.href = res.checkout_url
    } catch {
      setBuyingId(null)
    }
  }

  if (roleLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="size-6 animate-spin text-neutral-500" />
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">Scan Credits</h1>
        {role === "developer" ? (
          <p className="text-emerald-400 font-medium">Unlimited Scans (Developer)</p>
        ) : (
          <p className="text-neutral-400">
            You have{" "}
            <span className="text-emerald-400 font-semibold">
              {profile?.scan_credits ?? 0}
            </span>{" "}
            credit{(profile?.scan_credits ?? 0) !== 1 ? "s" : ""} remaining
          </p>
        )}
      </div>

      {success && (
        <div className="mx-auto max-w-md rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-4 text-center">
          <p className="text-emerald-400 font-medium">Purchase successful!</p>
          <p className="text-sm text-neutral-400 mt-1">Your credits have been added to your account.</p>
        </div>
      )}

      <div className="mx-auto max-w-4xl">
        <p className="text-center text-neutral-400 mb-2">1 credit = 1 scan. Your first scan is free.</p>
        <p className="text-center text-sm text-emerald-400 mb-10">1 Free Scan Included With Signup</p>

        <div className="grid md:grid-cols-3 gap-6">
          {PACKAGES.map((pkg) => (
            <div
              key={pkg.id}
              className={`rounded-xl border p-6 text-center ${
                pkg.highlight
                  ? "border-emerald-500/50 bg-emerald-500/5"
                  : "border-neutral-800 bg-neutral-900/50"
              }`}
            >
              {pkg.highlight && (
                <div className="text-xs font-semibold text-emerald-400 mb-2 uppercase tracking-wider">
                  Most Popular
                </div>
              )}
              <div className="text-lg font-semibold text-neutral-200 mb-1">{pkg.name}</div>
              <div className="text-3xl font-bold text-neutral-100 mb-1">{pkg.price}</div>
              <div className="text-sm text-neutral-500 mb-4">
                {pkg.credits} credit{pkg.credits > 1 ? "s" : ""} · {pkg.perScan}
              </div>
              <Button
                className={`w-full ${
                  pkg.highlight
                    ? "bg-emerald-600 hover:bg-emerald-700"
                    : "bg-neutral-800 hover:bg-neutral-700"
                }`}
                disabled={buyingId === pkg.id}
                onClick={() => handleBuy(pkg.id)}
              >
                {buyingId === pkg.id ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  "Buy"
                )}
              </Button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
