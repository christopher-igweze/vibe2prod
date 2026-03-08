ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'
    CHECK (role IN ('developer', 'beta_tester', 'user'));

-- Auto-promote Christopher (the only real user, has most scans)
UPDATE public.profiles SET role = 'developer'
  WHERE user_id = 'user_39iJDUPgGU8w4LE59ddfLNFpxrW';
