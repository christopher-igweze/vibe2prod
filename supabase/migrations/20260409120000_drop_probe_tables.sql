-- Drop security-probe subsystem tables.
--
-- The security-probe feature (live vulnerability scanning microservice) has
-- been fully removed from the vibe2prod backend and frontend. This migration
-- drops the tables that backed it.
--
-- Superseded migrations (files deleted in the same change):
--   - 20260310140000_probe_tables.sql
--   - 20260310160000_probe_anonymous_auth_method.sql

DROP TABLE IF EXISTS public.probe_findings CASCADE;
DROP TABLE IF EXISTS public.authorized_targets CASCADE;
DROP TABLE IF EXISTS public.probes CASCADE;
