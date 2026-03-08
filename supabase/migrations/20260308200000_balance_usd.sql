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
