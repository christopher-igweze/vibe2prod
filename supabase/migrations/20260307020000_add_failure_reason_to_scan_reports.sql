-- Add failure_reason column to scan_reports so the frontend can show
-- why a scan failed (rather than just "failed").
ALTER TABLE scan_reports ADD COLUMN IF NOT EXISTS failure_reason text;
