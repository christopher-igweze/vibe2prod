-- Allow 'forge' as a scan_tier value for FORGE engine scans
ALTER TABLE scan_reports
DROP CONSTRAINT IF EXISTS scan_reports_scan_tier_check;

ALTER TABLE scan_reports
ADD CONSTRAINT scan_reports_scan_tier_check
CHECK (scan_tier IN ('deep', 'free', 'forge'));

-- Also update projects constraint
ALTER TABLE projects
DROP CONSTRAINT IF EXISTS projects_latest_scan_tier_check;

ALTER TABLE projects
ADD CONSTRAINT projects_latest_scan_tier_check
CHECK (latest_scan_tier IS NULL OR latest_scan_tier IN ('deep', 'free', 'forge'));
