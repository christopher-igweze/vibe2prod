# Pay-As-You-Go Wallet Pricing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace integer credit packs ($10/$40/$99) with a dollar-balance wallet where scans cost (LLM + infra) x 4x markup, users pre-load funds (min $5), and new signups get $5 free.

**Architecture:** Add a `balance_usd NUMERIC(10,4)` column to profiles (default $5.00 for new users). After each scan, compute `charged_amount = (cost_usd + INFRA_COST_PER_SCAN) * 4`. Deduct from balance. Store `charged_amount` alongside `cost_usd` in the discovery report. Frontend shows both raw cost and amount charged.

**Tech Stack:** FastAPI + Supabase (PostgreSQL), Stripe Checkout (variable amount), Next.js + Clerk

---

## Constants

Based on FORGE benchmark data:
- **INFRA_COST_PER_SCAN = $0.14** (Fly.io 4GB RAM + 10GB storage for ~1 hour ≈ $0.09 compute + $0.05 storage)
- **COST_MARKUP = 4.0** (4x markup on raw costs)
- **MIN_DEPOSIT = 500** (cents, $5.00 minimum)
- **DEFAULT_SIGNUP_BALANCE = 5.00** ($5 free on signup)

---

### Task 1: Database Migration — balance_usd Column

**Files:**
- Create: `supabase/migrations/20260308200000_balance_usd.sql`

**Step 1: Write the migration**

```sql
-- Migrate from integer scan_credits to USD balance wallet
-- New users get $5.00 free balance; existing users get $5.00 per remaining credit

-- Add balance column
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS balance_usd NUMERIC(10,4) NOT NULL DEFAULT 5.0000;

-- Migrate existing credits: $5 per remaining credit
UPDATE public.profiles
  SET balance_usd = GREATEST(scan_credits * 5.0, 0)
  WHERE scan_credits IS NOT NULL AND scan_credits > 0;

-- Update credit_transactions to support decimal amounts
ALTER TABLE public.credit_transactions
  ALTER COLUMN amount TYPE NUMERIC(10,4) USING amount::NUMERIC(10,4);

ALTER TABLE public.credit_transactions
  ALTER COLUMN balance_after TYPE NUMERIC(10,4) USING balance_after::NUMERIC(10,4);

-- Add charged_amount to track what users were charged per scan
ALTER TABLE public.credit_transactions
  ADD COLUMN IF NOT EXISTS scan_id UUID;

-- Add description column for clearer transaction history
ALTER TABLE public.credit_transactions
  ADD COLUMN IF NOT EXISTS description TEXT;
```

**Step 2: Apply migration locally**

Run: `cd backend && npx supabase db push` (or apply via Supabase dashboard)

**Step 3: Commit**

```bash
git add supabase/migrations/20260308200000_balance_usd.sql
git commit -m "🗃️ migration: add balance_usd column, convert credit_transactions to decimal"
```

---

### Task 2: Backend Models — Replace Credit Packages with Wallet Config

**Files:**
- Modify: `backend/models/credits.py` (full rewrite)

**Step 1: Rewrite credits.py**

```python
"""Wallet-based pricing models and constants."""

from __future__ import annotations

from pydantic import BaseModel

# Pricing constants
INFRA_COST_PER_SCAN: float = 0.14  # Container + storage per scan (~1hr)
COST_MARKUP: float = 4.0           # 4x markup on raw costs
MIN_DEPOSIT_CENTS: int = 500       # $5.00 minimum deposit

# Pre-set deposit options shown on the pricing page
DEPOSIT_OPTIONS = [
    {"id": "deposit_5", "amount_cents": 500, "label": "$5"},
    {"id": "deposit_20", "amount_cents": 2000, "label": "$20"},
    {"id": "deposit_50", "amount_cents": 5000, "label": "$50"},
]


def compute_scan_charge(llm_cost_usd: float) -> dict:
    """Compute the total charge for a scan.

    Returns dict with raw_cost, infra_cost, total_before_markup, charged_amount.
    """
    infra_cost = INFRA_COST_PER_SCAN
    total_raw = llm_cost_usd + infra_cost
    charged = round(total_raw * COST_MARKUP, 4)
    return {
        "llm_cost": round(llm_cost_usd, 4),
        "infra_cost": round(infra_cost, 4),
        "total_raw": round(total_raw, 4),
        "markup": COST_MARKUP,
        "charged_amount": charged,
    }


class DepositRequest(BaseModel):
    amount_cents: int  # Must be >= MIN_DEPOSIT_CENTS


class WalletBalance(BaseModel):
    balance_usd: float
    transactions: list[dict] = []
```

**Step 2: Commit**

```bash
git add backend/models/credits.py
git commit -m "✨ feat(models): replace credit packages with wallet pricing constants"
```

---

### Task 3: Backend Supabase Client — Wallet Functions

**Files:**
- Modify: `backend/services/supabase_client.py` (lines 801-888)

**Step 1: Replace credit functions with wallet functions**

Replace `get_user_credits` (lines 801-813) with:

```python
def get_user_balance(user_id: str) -> float:
    """Return the user's current USD wallet balance."""
    client = _client()
    row = (
        client.table("profiles")
        .select("balance_usd")
        .eq("user_id", str(user_id))
        .limit(1)
        .execute()
    )
    if not row.data:
        return 0.0
    return float(row.data[0].get("balance_usd", 0))
```

Replace `deduct_credit` (lines 816-841) with:

```python
def deduct_balance(
    user_id: str,
    amount: float,
    scan_id: str | None = None,
    description: str | None = None,
) -> float:
    """Deduct a USD amount from the user's wallet and log a usage transaction.

    Raises ValueError if the user has insufficient balance.
    Returns the new balance.
    """
    client = _client()
    current = get_user_balance(user_id)
    if current < amount:
        raise ValueError(f"Insufficient balance: ${current:.2f} < ${amount:.2f}")

    new_balance = round(current - amount, 4)
    client.table("profiles").update(
        {"balance_usd": new_balance}
    ).eq("user_id", str(user_id)).execute()

    tx: dict = {
        "user_id": str(user_id),
        "amount": round(-amount, 4),
        "balance_after": new_balance,
        "type": "usage",
    }
    if scan_id:
        tx["scan_id"] = scan_id
    if description:
        tx["description"] = description
    client.table("credit_transactions").insert(tx).execute()

    return new_balance
```

Replace `add_credits` (lines 844-874) with:

```python
def add_balance(
    user_id: str,
    amount_usd: float,
    stripe_session_id: str | None = None,
    description: str | None = None,
) -> float:
    """Add USD to a user's wallet balance and log a purchase transaction.

    Returns the new balance.
    """
    client = _client()
    current = get_user_balance(user_id)
    new_balance = round(current + amount_usd, 4)

    client.table("profiles").update(
        {"balance_usd": new_balance}
    ).eq("user_id", str(user_id)).execute()

    tx: dict = {
        "user_id": str(user_id),
        "amount": round(amount_usd, 4),
        "balance_after": new_balance,
        "type": "purchase",
    }
    if stripe_session_id:
        tx["stripe_session_id"] = stripe_session_id
    if description:
        tx["description"] = description
    client.table("credit_transactions").insert(tx).execute()

    return new_balance
```

Keep `get_credit_transactions` unchanged (line 877-888) — it already works with the new schema.

Also keep `get_user_credits` as a deprecated alias for backwards compat during migration:

```python
# Deprecated — use get_user_balance
get_user_credits = get_user_balance
```

Wait, no — delete it. We'll update all call sites.

**Step 2: Commit**

```bash
git add backend/services/supabase_client.py
git commit -m "✨ feat(db): replace integer credit functions with USD wallet balance"
```

---

### Task 4: Backend Audit Route — Charge Actual Cost After Scan

**Files:**
- Modify: `backend/api/routes/audit.py` (lines 60-65 and 126-131)

**Step 1: Update pre-scan balance check (lines 126-131)**

Replace:
```python
# Credit check: developers get unlimited scans, everyone else needs credits
if role != "developer" and db.get_user_credits(user_id) <= 0:
    raise _limit_exception(
        "no_credits",
        "You have no scan credits remaining. Purchase more to continue scanning.",
    )
```

With:
```python
# Balance check: developers get unlimited scans, everyone else needs funds
if role != "developer" and db.get_user_balance(user_id) <= 0:
    raise _limit_exception(
        "no_balance",
        "Your wallet balance is $0.00. Add funds to continue scanning.",
    )
```

**Step 2: Update post-scan deduction (lines 60-65)**

Replace:
```python
# Deduct credit after successful scan (developers are exempt)
if user_id and role != "developer":
    try:
        db.deduct_credit(user_id)
    except ValueError:
        logger.warning("Could not deduct credit for user %s (scan %s)", user_id, scan_id)
```

With:
```python
# Charge actual cost after successful scan (developers are exempt)
if user_id and role != "developer":
    try:
        from models.credits import compute_scan_charge
        charge = compute_scan_charge(result.cost_usd)
        db.deduct_balance(
            user_id,
            charge["charged_amount"],
            scan_id=str(scan_id),
            description=f"Scan: LLM ${charge['llm_cost']:.2f} + Infra ${charge['infra_cost']:.2f} = ${charge['total_raw']:.2f} x {charge['markup']}x",
        )
        logger.info(
            "Charged $%.4f for scan %s (LLM: $%.4f, infra: $%.4f, markup: %.1fx)",
            charge["charged_amount"], scan_id, charge["llm_cost"], charge["infra_cost"], charge["markup"],
        )
    except ValueError:
        logger.warning("Insufficient balance for user %s (scan %s) — scan ran but charge failed", user_id, scan_id)
```

**Step 3: Add import at top of file**

No extra import needed — `compute_scan_charge` is imported inline.

**Step 4: Commit**

```bash
git add backend/api/routes/audit.py
git commit -m "✨ feat(audit): charge actual (LLM+infra)x4 cost after scan instead of flat credit"
```

---

### Task 5: Backend Credits Routes — Add Funds Flow

**Files:**
- Modify: `backend/api/routes/credits.py` (full rewrite)

**Step 1: Rewrite credits routes**

```python
"""Wallet management routes: balance, deposits, Stripe checkout, and webhook."""

from __future__ import annotations

import logging

import stripe
from fastapi import APIRouter, HTTPException, Request
from starlette.responses import JSONResponse

from api.middleware.rate_limit import limiter, rate_limit_string
from config import settings
from models.credits import (
    DEPOSIT_OPTIONS,
    MIN_DEPOSIT_CENTS,
    DepositRequest,
    WalletBalance,
)
import services.supabase_client as db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/credits")
@limiter.limit(rate_limit_string())
async def get_balance(request: Request) -> dict:
    """Return the authenticated user's wallet balance and recent transactions."""
    user_id: str = request.state.user_id
    balance = db.get_user_balance(user_id)
    transactions = db.get_credit_transactions(user_id)
    return WalletBalance(balance_usd=balance, transactions=transactions).model_dump()


@router.get("/credits/packages")
@limiter.limit(rate_limit_string())
async def get_deposit_options(request: Request) -> list[dict]:
    """Return suggested deposit amounts."""
    return DEPOSIT_OPTIONS


@router.post("/credits/checkout")
@limiter.limit(rate_limit_string())
async def create_checkout(request_body: DepositRequest, request: Request) -> dict:
    """Create a Stripe Checkout Session for a wallet deposit."""
    user_id: str = request.state.user_id

    if request_body.amount_cents < MIN_DEPOSIT_CENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Minimum deposit is ${MIN_DEPOSIT_CENTS / 100:.2f}",
        )

    if not settings.stripe_secret_key:
        raise HTTPException(status_code=503, detail="Stripe is not configured")

    stripe.api_key = settings.stripe_secret_key

    amount_dollars = request_body.amount_cents / 100

    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[
            {
                "price_data": {
                    "currency": "usd",
                    "unit_amount": request_body.amount_cents,
                    "product_data": {
                        "name": f"Vibe2Prod Wallet — ${amount_dollars:.2f}",
                    },
                },
                "quantity": 1,
            }
        ],
        metadata={
            "user_id": user_id,
            "deposit_amount_cents": str(request_body.amount_cents),
        },
        success_url=f"{settings.frontend_url}/pricing?success=true",
        cancel_url=f"{settings.frontend_url}/pricing",
    )

    return {"checkout_url": session.url}


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request) -> JSONResponse:
    """Handle Stripe webhook events (no auth required — signature verified)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not settings.stripe_webhook_secret:
        logger.error("Stripe webhook secret not configured")
        raise HTTPException(status_code=503, detail="Stripe webhook not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        amount_cents_str = metadata.get("deposit_amount_cents")

        if not user_id or not amount_cents_str:
            logger.warning("Stripe webhook missing metadata: %s", metadata)
            return JSONResponse(content={"status": "ignored"})

        amount_usd = int(amount_cents_str) / 100

        db.add_balance(
            user_id=user_id,
            amount_usd=amount_usd,
            stripe_session_id=session.get("id"),
            description=f"Deposit: ${amount_usd:.2f}",
        )
        logger.info(
            "Added $%.2f to wallet for user %s",
            amount_usd, user_id,
        )

    return JSONResponse(content={"status": "ok"})
```

**Step 2: Commit**

```bash
git add backend/api/routes/credits.py
git commit -m "✨ feat(credits): replace package checkout with variable-amount wallet deposits"
```

---

### Task 6: Backend User Route — Return balance_usd

**Files:**
- Modify: `backend/api/routes/user.py` (line 29)

**Step 1: Update fallback profile to use balance_usd**

Change line 29 from:
```python
"scan_credits": 1,
```
To:
```python
"scan_credits": 1,
"balance_usd": 0.0,
```

(Keep scan_credits for backwards compat until frontend is updated)

**Step 2: Commit**

```bash
git add backend/api/routes/user.py
git commit -m "🔧 fix(user): include balance_usd in fallback profile response"
```

---

### Task 7: Frontend Types — Add Wallet Fields

**Files:**
- Modify: `frontend/src/lib/api/types.ts` (lines 323-333 and 335-340)

**Step 1: Add balance_usd to UserProfile**

Add after `scan_credits: number` (line 329):
```typescript
  balance_usd: number
```

**Step 2: Update CreditPackage to DepositOption**

Replace `CreditPackage` interface (lines 335-340) with:
```typescript
export interface DepositOption {
  id: string
  amount_cents: number
  label: string
}
```

**Step 3: Commit**

```bash
git add frontend/src/lib/api/types.ts
git commit -m "✨ feat(types): add balance_usd to UserProfile, DepositOption interface"
```

---

### Task 8: Frontend Hook — Support balance_usd

**Files:**
- Modify: `frontend/src/hooks/use-user-role.ts` (line 33)

**Step 1: Add balance_usd to fallback profile**

Change line 33 from:
```typescript
scan_credits: 0,
```
To:
```typescript
scan_credits: 0,
balance_usd: 0,
```

**Step 2: Commit**

```bash
git add frontend/src/hooks/use-user-role.ts
git commit -m "🔧 fix(hooks): include balance_usd in fallback profile"
```

---

### Task 9: Frontend Pricing Page — "Add Funds" UI

**Files:**
- Modify: `frontend/src/app/(app)/pricing/page.tsx` (full rewrite)

**Step 1: Rewrite pricing page**

```tsx
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
```

**Step 2: Commit**

```bash
git add frontend/src/app/\\(app\\)/pricing/page.tsx
git commit -m "✨ feat(pricing): replace credit packs with wallet deposit UI"
```

---

### Task 10: Frontend Dashboard — Show Dollar Balance

**Files:**
- Modify: `frontend/src/app/(app)/dashboard/page.tsx` (lines 159-181)

**Step 1: Replace credit display with balance display**

Replace lines 159-181:

```typescript
{role === "developer" ? (
  <div className="text-sm text-emerald-400">Unlimited Scans</div>
) : (profile?.scan_credits ?? 0) === 0 ? (
  <Card className="border-amber-500/30 bg-amber-500/5 p-4">
    <div className="flex items-center justify-between">
      <p className="text-amber-400 text-sm font-medium">No scan credits remaining</p>
      <Link href="/pricing">
        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
          Buy Credits
        </Button>
      </Link>
    </div>
  </Card>
) : (
  <div className="flex items-center gap-3 text-sm">
    <span className="text-neutral-400">
      <span className="text-emerald-400 font-semibold">{profile?.scan_credits}</span> scan credit{(profile?.scan_credits ?? 0) !== 1 ? "s" : ""} remaining
    </span>
    <Link href="/pricing" className="text-emerald-400 hover:text-emerald-300 underline text-xs">
      Buy More
    </Link>
  </div>
)}
```

With:

```typescript
{role === "developer" ? (
  <div className="text-sm text-emerald-400">Unlimited Scans</div>
) : (profile?.balance_usd ?? 0) <= 0 ? (
  <Card className="border-amber-500/30 bg-amber-500/5 p-4">
    <div className="flex items-center justify-between">
      <p className="text-amber-400 text-sm font-medium">Wallet balance is $0.00</p>
      <Link href="/pricing">
        <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700">
          Add Funds
        </Button>
      </Link>
    </div>
  </Card>
) : (
  <div className="flex items-center gap-3 text-sm">
    <span className="text-neutral-400">
      Balance: <span className="text-emerald-400 font-semibold">${(profile?.balance_usd ?? 0).toFixed(2)}</span>
    </span>
    <Link href="/pricing" className="text-emerald-400 hover:text-emerald-300 underline text-xs">
      Add Funds
    </Link>
  </div>
)}
```

**Step 2: Commit**

```bash
git add frontend/src/app/\\(app\\)/dashboard/page.tsx
git commit -m "✨ feat(dashboard): show wallet balance instead of credit count"
```

---

### Task 11: Frontend Report — Show Charged Amount

**Files:**
- Modify: `frontend/src/app/(app)/scan/[scanId]/report/_components/report-header.tsx` (lines 143-147)
- Modify: `frontend/src/app/(app)/scan/[scanId]/report/_components/report-utils.ts` (add formatCharge)

**Step 1: Add formatCharge to report-utils.ts**

Add after `formatCost`:

```typescript
export function formatCharge(costUsd: number): string {
  const infraCost = 0.14
  const markup = 4
  const charged = (costUsd + infraCost) * markup
  return `$${charged.toFixed(2)}`
}
```

**Step 2: Update report-header.tsx cost badge (lines 143-147)**

Replace:
```tsx
{report.cost_usd > 0 && (
  <Badge variant="outline" className="border-neutral-700 text-neutral-300">
    {formatCost(report.cost_usd)}
  </Badge>
)}
```

With:
```tsx
{report.cost_usd > 0 && (
  <>
    <Badge variant="outline" className="border-emerald-700/50 text-emerald-300">
      Charged: {formatCharge(report.cost_usd)}
    </Badge>
    <Badge variant="outline" className="border-neutral-700 text-neutral-500">
      Raw: {formatCost(report.cost_usd)}
    </Badge>
  </>
)}
```

**Step 3: Import formatCharge in report-header.tsx**

Update import line 25:
```typescript
import { formatDuration, formatCost, formatCharge } from "./report-utils"
```

**Step 4: Also update to-markdown.ts and to-pdf-html.ts**

In `frontend/src/lib/report/to-markdown.ts` line 233, update to include charged amount.
In `frontend/src/lib/report/to-pdf-html.ts` line 182, same.

**Step 5: Commit**

```bash
git add frontend/src/app/\\(app\\)/scan/\\[scanId\\]/report/_components/report-utils.ts
git add frontend/src/app/\\(app\\)/scan/\\[scanId\\]/report/_components/report-header.tsx
git add frontend/src/lib/report/to-markdown.ts
git add frontend/src/lib/report/to-pdf-html.ts
git commit -m "✨ feat(report): show charged amount (4x markup) alongside raw LLM cost"
```

---

### Task 12: Landing Page Pricing Section — Update Copy

**Files:**
- Modify: `frontend/src/app/page.tsx` (pricing section)

**Step 1: Find and update the pricing section**

Update the hardcoded pricing tiers in the landing page to reflect wallet model:
- Change heading from "Ship Confidently. Pay Per Scan." to "Pay Only For What You Use."
- Remove credit pack tiers
- Show wallet concept: "$5 free on signup", estimated costs per repo size
- CTA: "Start Free" → links to signup

**Step 2: Commit**

```bash
git add frontend/src/app/page.tsx
git commit -m "📝 copy(landing): update pricing section for pay-as-you-go wallet model"
```

---

### Task 13: Build Verification

**Step 1: Run backend tests**

Run: `cd backend && PYTHONPATH=. pytest -q`
Expected: All tests pass (fix any that reference old credit functions)

**Step 2: Run frontend build**

Run: `cd frontend && npm run build`
Expected: Zero errors

**Step 3: Search for stale references**

Run: `grep -r "scan_credits\|CREDIT_PACKAGES\|deduct_credit\|add_credits\|get_user_credits\|package_id" backend/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx" | grep -v node_modules | grep -v .next`

Expected: No stale references to old credit system (except possibly in migration SQL)

**Step 4: Commit any fixes**

---

### Task 14: Migration — Apply to Supabase

**Step 1: Apply migration to remote Supabase**

This needs to be done via Supabase dashboard or CLI. The migration:
1. Adds `balance_usd NUMERIC(10,4) DEFAULT 5.0` to profiles
2. Converts existing credits to $5/credit in balance_usd
3. Alters credit_transactions columns to NUMERIC(10,4)
4. Adds scan_id and description columns to credit_transactions

**Step 2: Verify in Supabase dashboard**

- Check profiles table has balance_usd column
- Check credit_transactions has numeric amount/balance_after columns

---

## File Summary

| File | Action |
|------|--------|
| `supabase/migrations/20260308200000_balance_usd.sql` | CREATE — DB migration |
| `backend/models/credits.py` | REWRITE — wallet constants + compute_scan_charge |
| `backend/services/supabase_client.py` | MODIFY — replace credit functions with balance functions |
| `backend/api/routes/audit.py` | MODIFY — charge actual cost after scan |
| `backend/api/routes/credits.py` | REWRITE — wallet deposit flow |
| `backend/api/routes/user.py` | MODIFY — add balance_usd to fallback |
| `frontend/src/lib/api/types.ts` | MODIFY — add balance_usd, DepositOption |
| `frontend/src/hooks/use-user-role.ts` | MODIFY — add balance_usd fallback |
| `frontend/src/app/(app)/pricing/page.tsx` | REWRITE — wallet deposit UI |
| `frontend/src/app/(app)/dashboard/page.tsx` | MODIFY — show $ balance |
| `frontend/src/app/(app)/scan/[scanId]/report/_components/report-header.tsx` | MODIFY — show charged amount |
| `frontend/src/app/(app)/scan/[scanId]/report/_components/report-utils.ts` | MODIFY — add formatCharge |
| `frontend/src/lib/report/to-markdown.ts` | MODIFY — include charged amount |
| `frontend/src/lib/report/to-pdf-html.ts` | MODIFY — include charged amount |
| `frontend/src/app/page.tsx` | MODIFY — update pricing section copy |
