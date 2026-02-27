-- Add lifetime scan tracking for waitlist users (5 free scans).
-- Clerk handles the waitlist queue; these columns track usage after approval.

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS lifetime_scans_used integer NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS lifetime_scan_cap integer NOT NULL DEFAULT 5;
