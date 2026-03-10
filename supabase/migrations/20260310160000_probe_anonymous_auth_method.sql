-- Allow 'anonymous' as an auth_method for probes started without sign-in.
ALTER TABLE public.probes DROP CONSTRAINT IF EXISTS probes_auth_method_check;
ALTER TABLE public.probes ADD CONSTRAINT probes_auth_method_check
  CHECK (auth_method IN ('dns_txt', 'meta_tag', 'http_header', 'file_upload', 'manual_approve', 'anonymous'));
