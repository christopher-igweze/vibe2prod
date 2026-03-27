-- Add encrypted OpenRouter API key column for BYOK (Bring Your Own Key) support.
-- Users who supply their own key pay OpenRouter directly; no wallet deduction.
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS openrouter_key_encrypted TEXT;
