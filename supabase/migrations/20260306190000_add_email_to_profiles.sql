-- Add email column to profiles table (required by Clerk webhook sync)
ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS email TEXT;
