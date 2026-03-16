-- API key hash column on profiles (for CLI authentication)
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS api_key_hash TEXT;

-- Index for fast API key lookup (hash → user_id)
CREATE INDEX IF NOT EXISTS idx_profiles_api_key_hash
  ON public.profiles (api_key_hash)
  WHERE api_key_hash IS NOT NULL;

-- Telemetry events table (anonymous + optionally linked to user via API key)
CREATE TABLE IF NOT EXISTS public.telemetry_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event TEXT NOT NULL,
  user_id TEXT,                    -- NULL for anonymous, set when API key provided
  machine_id TEXT DEFAULT '',
  version TEXT DEFAULT '',
  model TEXT DEFAULT '',
  mode TEXT DEFAULT '',
  findings_count INTEGER DEFAULT 0,
  duration_seconds DOUBLE PRECISION DEFAULT 0,
  cost_usd DOUBLE PRECISION DEFAULT 0,
  findings JSONB,                  -- opt-in shared findings
  repo_profile JSONB,              -- language/framework stats
  timestamp TEXT DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- No RLS on telemetry — backend service role writes, no user access needed
ALTER TABLE public.telemetry_events ENABLE ROW LEVEL SECURITY;

-- Service role can do everything (backend uses service key)
CREATE POLICY "Service role full access on telemetry_events"
  ON public.telemetry_events
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Index for querying by user_id (linked CLI users)
CREATE INDEX IF NOT EXISTS idx_telemetry_events_user_id
  ON public.telemetry_events (user_id)
  WHERE user_id IS NOT NULL;

-- Index for querying by event type
CREATE INDEX IF NOT EXISTS idx_telemetry_events_event
  ON public.telemetry_events (event);
