-- Increase default signup balance from $5 to $15
-- Gives new users minimum 3 scans across all repo sizes

ALTER TABLE public.profiles
  ALTER COLUMN balance_usd SET DEFAULT 15.0000;

-- Update existing users who still have the original $5 default (haven't spent or deposited)
UPDATE public.profiles
  SET balance_usd = 15.0000
  WHERE balance_usd = 5.0000;
