-- Add scan_report_id to fix_attempts for scan-level remediation
-- (existing action_item_id is for per-action-item fixes)
ALTER TABLE public.fix_attempts
ADD COLUMN IF NOT EXISTS scan_report_id UUID REFERENCES public.scan_reports(id) ON DELETE CASCADE;

-- Make action_item_id nullable (scan-level fixes don't have one)
ALTER TABLE public.fix_attempts
ALTER COLUMN action_item_id DROP NOT NULL;

-- Index for scan-level fix lookups
CREATE INDEX IF NOT EXISTS idx_fix_attempts_scan_report_id
ON public.fix_attempts(scan_report_id);
