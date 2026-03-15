-- OAuth state nonce consumption tracking (replay-attack prevention, CWE-613)
-- This table tracks consumed state tokens to prevent replay attacks within the TTL window.

CREATE TABLE IF NOT EXISTS public.oauth_state_nonces (
    jti         TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    consumed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at  TIMESTAMPTZ NOT NULL
);

-- Index for efficient cleanup of expired nonces
CREATE INDEX IF NOT EXISTS idx_oauth_state_nonces_expires_at
    ON public.oauth_state_nonces (expires_at);

-- Enable RLS for security
ALTER TABLE public.oauth_state_nonces ENABLE ROW LEVEL SECURITY;

-- Only allow service role to access this table (internal use only)
CREATE POLICY IF NOT EXISTS service_role_only ON public.oauth_state_nonces
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
