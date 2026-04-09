-- Drop stale lifetime_scan_cap columns from profiles.
--
-- The free-tier model is $15 signup credit (tracked via balance_usd),
-- not a 5-scan hard cap. These columns were carried on UserProfile but
-- never read for gating — pure dead weight. Removed from backend and
-- frontend in commit d8ac95c.
--
-- Supersedes: 20260226120000_lifetime_scan_cap.sql

ALTER TABLE public.profiles
  DROP COLUMN IF EXISTS lifetime_scans_used,
  DROP COLUMN IF EXISTS lifetime_scan_cap;
