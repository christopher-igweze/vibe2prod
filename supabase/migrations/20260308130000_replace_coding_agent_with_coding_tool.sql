-- Replace coding_agent_provider/coding_agent_model with coding_tool/coding_tool_other
-- and simplify acquisition_source options (add threads)

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS coding_tool TEXT,
  ADD COLUMN IF NOT EXISTS coding_tool_other TEXT;

-- Migrate existing data: map old provider to closest tool
UPDATE public.profiles
SET coding_tool = CASE
  WHEN coding_agent_provider = 'anthropic' THEN 'claude_code'
  WHEN coding_agent_provider = 'openai' THEN 'codex'
  ELSE 'other'
END
WHERE coding_agent_provider IS NOT NULL AND coding_tool IS NULL;
