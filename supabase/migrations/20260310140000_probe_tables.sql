-- Live Application Testing Suite: probe tables
-- Stores probes, probe findings, and authorized targets for domain verification.

-- ------------------------------------------------------------------ --
-- probes
-- ------------------------------------------------------------------ --
CREATE TABLE public.probes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  project_id UUID REFERENCES public.projects(id) ON DELETE SET NULL,
  user_id TEXT NOT NULL,
  target_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
  probe_type TEXT NOT NULL DEFAULT 'security'
    CHECK (probe_type IN ('security', 'functionality', 'performance', 'accessibility', 'full')),
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  total_findings INTEGER DEFAULT 0,
  critical_count INTEGER DEFAULT 0,
  high_count INTEGER DEFAULT 0,
  medium_count INTEGER DEFAULT 0,
  low_count INTEGER DEFAULT 0,
  probe_score INTEGER,
  report_data JSONB,
  auth_method TEXT CHECK (auth_method IN ('dns_txt', 'meta_tag', 'http_header', 'file_upload', 'manual_approve')),
  auth_verified_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  duration_seconds FLOAT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.probes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own probes"
  ON public.probes FOR SELECT
  USING (user_id = requesting_user_id());

CREATE POLICY "Users can insert their own probes"
  ON public.probes FOR INSERT
  WITH CHECK (user_id = requesting_user_id());

CREATE POLICY "Users can update their own probes"
  ON public.probes FOR UPDATE
  USING (user_id = requesting_user_id());

CREATE INDEX idx_probes_user_id ON public.probes (user_id);
CREATE INDEX idx_probes_project_id ON public.probes (project_id);
CREATE INDEX idx_probes_target_url ON public.probes (target_url);

-- ------------------------------------------------------------------ --
-- probe_findings
-- ------------------------------------------------------------------ --
CREATE TABLE public.probe_findings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  probe_id UUID NOT NULL REFERENCES public.probes(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL,
  severity TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
  url_tested TEXT NOT NULL,
  method TEXT,
  request_summary TEXT,
  response_summary TEXT,
  evidence TEXT,
  owasp_category TEXT,
  cwe_id TEXT,
  confidence FLOAT DEFAULT 0.0,
  false_positive BOOLEAN DEFAULT false,
  linked_scan_finding_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE public.probe_findings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own probe findings"
  ON public.probe_findings FOR SELECT
  USING (user_id = requesting_user_id());

CREATE POLICY "Users can insert their own probe findings"
  ON public.probe_findings FOR INSERT
  WITH CHECK (user_id = requesting_user_id());

CREATE INDEX idx_probe_findings_probe_id ON public.probe_findings (probe_id);

-- ------------------------------------------------------------------ --
-- authorized_targets
-- ------------------------------------------------------------------ --
CREATE TABLE public.authorized_targets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id TEXT NOT NULL,
  domain TEXT NOT NULL,
  auth_method TEXT NOT NULL,
  verified_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, domain)
);

ALTER TABLE public.authorized_targets ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own authorized targets"
  ON public.authorized_targets FOR SELECT
  USING (user_id = requesting_user_id());

CREATE POLICY "Users can insert their own authorized targets"
  ON public.authorized_targets FOR INSERT
  WITH CHECK (user_id = requesting_user_id());

CREATE POLICY "Users can update their own authorized targets"
  ON public.authorized_targets FOR UPDATE
  USING (user_id = requesting_user_id());
