-- Forgeignore training data — anonymized suppression patterns for model improvement
CREATE TABLE IF NOT EXISTS public.forgeignore_entries (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  fingerprint TEXT NOT NULL UNIQUE,
  user_id TEXT,
  repo_hash TEXT NOT NULL,
  pattern TEXT NOT NULL,
  category TEXT NOT NULL,
  reason TEXT NOT NULL,
  type TEXT NOT NULL DEFAULT 'false_positive',
  check_id TEXT,
  path_glob TEXT,
  max_severity TEXT,
  scan_mode TEXT DEFAULT 'full',
  version TEXT DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- RLS: service role full access, no direct user access
ALTER TABLE public.forgeignore_entries ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on forgeignore_entries"
  ON public.forgeignore_entries
  FOR ALL
  USING (true)
  WITH CHECK (true);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_forgeignore_user_id
  ON public.forgeignore_entries (user_id)
  WHERE user_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_forgeignore_category
  ON public.forgeignore_entries (category);

CREATE INDEX IF NOT EXISTS idx_forgeignore_type
  ON public.forgeignore_entries (type);
