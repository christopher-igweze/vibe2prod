-- Remove the beta_tester role and relax the profiles.role CHECK constraint.
--
-- The beta/waitlist model is gone. Roles are now:
--   developer — unlimited, bypasses billing
--   user      — normal tier, full access, pays from wallet or via BYOK
--
-- Any remaining beta_tester profiles are downgraded to 'user' (they already
-- have full access under the new model).

UPDATE public.profiles SET role = 'user' WHERE role = 'beta_tester';

ALTER TABLE public.profiles
  DROP CONSTRAINT IF EXISTS profiles_role_check;

ALTER TABLE public.profiles
  ADD CONSTRAINT profiles_role_check
    CHECK (role IN ('developer', 'user'));
