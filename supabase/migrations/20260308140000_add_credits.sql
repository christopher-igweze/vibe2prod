-- Add credits to profiles (1 free scan for new users)
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS scan_credits INTEGER NOT NULL DEFAULT 1;

-- Credit transaction history
CREATE TABLE IF NOT EXISTS public.credit_transactions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL REFERENCES public.profiles(user_id),
  amount INTEGER NOT NULL,
  balance_after INTEGER NOT NULL,
  type TEXT NOT NULL,
  stripe_session_id TEXT,
  package_name TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_credit_tx_user ON public.credit_transactions(user_id);
