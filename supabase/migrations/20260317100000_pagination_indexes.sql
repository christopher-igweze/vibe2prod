-- Composite indexes for paginated list queries.
-- These cover the most common access patterns: listing a user's resources
-- ordered by created_at DESC, and looking up findings by scan_id.

-- Scans: /api/user/scans (list_user_scans, count_user_scans)
CREATE INDEX IF NOT EXISTS idx_scan_reports_user_created
    ON scan_reports (user_id, created_at DESC);

-- Projects: /api/user/projects (list_user_projects, count_user_projects)
CREATE INDEX IF NOT EXISTS idx_projects_user_created
    ON projects (user_id, created_at DESC);

-- Probes: /api/user/probes (list_user_probes)
CREATE INDEX IF NOT EXISTS idx_probes_user_created
    ON probes (user_id, created_at DESC);
