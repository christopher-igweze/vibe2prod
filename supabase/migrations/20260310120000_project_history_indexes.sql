CREATE INDEX IF NOT EXISTS idx_scan_reports_project_created
  ON public.scan_reports(project_id, created_at DESC);
