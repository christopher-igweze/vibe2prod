-- Add branch column to scan_reports so we know which branch was scanned
ALTER TABLE scan_reports ADD COLUMN IF NOT EXISTS branch TEXT;
